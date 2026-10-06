// A small JSON Schema validator for the keywords docs/seed-format.schema.json uses, so the page
// can check a seed from ZORA or a file without a library. It throws on any other keyword, so a
// schema change it cannot check is noticed rather than half-checked.
//
// Type-checked with JSDoc (scripts/check_site.mjs runs tsc).
// @ts-check
"use strict";

const SUPPORTED_KEYWORDS = new Set([
  "$schema", "$id", "title", "description", "$defs", "$ref", "type", "const", "enum", "pattern",
  "minLength", "maxLength", "minimum", "maximum", "minItems", "maxItems", "required", "properties",
  "items", "anyOf",
]);

/**
 * The JSON type of a value, with "integer" for whole numbers.
 * @param {unknown} value
 */
function jsonType(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  if (typeof value === "number") return Number.isInteger(value) ? "integer" : "number";
  return typeof value;
}

/**
 * Checks a value against a schema.
 * @param {any} root  The schema; its "$defs" resolve "#/$defs/<name>" references.
 * @param {unknown} value
 * @returns {string[]} The problems found, each "<path>: <what>"; empty when the value is valid.
 */
function validateJsonSchema(root, value) {
  /** @type {string[]} */
  const errors = [];

  /**
   * @param {any} schema
   * @param {unknown} node
   * @param {string} path
   * @param {string[]} out
   */
  function check(schema, node, path, out) {
    for (const keyword of Object.keys(schema)) {
      if (!SUPPORTED_KEYWORDS.has(keyword)) throw new Error(`the validator does not support "${keyword}"`);
    }
    if (schema.$ref !== undefined) {
      const name = String(schema.$ref).replace(/^#\/\$defs\//, "");
      if (!root.$defs || !root.$defs[name]) throw new Error(`unknown reference ${schema.$ref}`);
      check(root.$defs[name], node, path, out);
    }
    const type = jsonType(node);
    const where = path || "the seed";
    if (schema.type !== undefined && !(type === schema.type || (schema.type === "number" && type === "integer"))) {
      out.push(`${where}: should be ${schema.type === "integer" ? "a whole number" : `of type ${schema.type}`}, not ${type}`);
      return;
    }
    if (schema.const !== undefined && node !== schema.const) out.push(`${where}: should be ${JSON.stringify(schema.const)}`);
    if (schema.enum !== undefined && !schema.enum.includes(node)) {
      out.push(`${where}: ${JSON.stringify(node)} is not one of the allowed values`);
    }
    if (typeof node === "string") {
      if (schema.pattern !== undefined && !new RegExp(schema.pattern, "u").test(node)) {
        out.push(`${where}: ${JSON.stringify(node)} does not have the expected form`);
      }
      if (schema.minLength !== undefined && node.length < schema.minLength) out.push(`${where}: is too short`);
      if (schema.maxLength !== undefined && node.length > schema.maxLength) out.push(`${where}: is too long`);
    }
    if (typeof node === "number") {
      if (schema.minimum !== undefined && node < schema.minimum) out.push(`${where}: should be at least ${schema.minimum}`);
      if (schema.maximum !== undefined && node > schema.maximum) out.push(`${where}: should be at most ${schema.maximum}`);
    }
    if (Array.isArray(node)) {
      if (schema.minItems !== undefined && node.length < schema.minItems) out.push(`${where}: has too few entries`);
      if (schema.maxItems !== undefined && node.length > schema.maxItems) out.push(`${where}: has too many entries`);
      if (schema.items !== undefined) node.forEach((item, i) => check(schema.items, item, `${path}[${i}]`, out));
    }
    if (type === "object") {
      const object = /** @type {Record<string, unknown>} */ (node);
      for (const name of schema.required || []) {
        if (!Object.prototype.hasOwnProperty.call(object, name)) out.push(`${where}: "${name}" is missing`);
      }
      for (const [name, sub] of Object.entries(schema.properties || {})) {
        if (Object.prototype.hasOwnProperty.call(object, name)) {
          check(sub, object[name], path ? `${path}.${name}` : name, out);
        }
      }
    }
    if (schema.anyOf !== undefined) {
      /** @type {string[][]} */
      const attempts = schema.anyOf.map((/** @type {any} */ option) => {
        /** @type {string[]} */
        const found = [];
        check(option, node, path, found);
        return found;
      });
      if (!attempts.some((found) => found.length === 0)) {
        // Report the closest option's problems: usually the form the producer meant.
        attempts.sort((a, b) => a.length - b.length);
        out.push(...(attempts[0].length ? attempts[0] : [`${where}: does not match any allowed form`]));
      }
    }
  }

  check(root, value, "", errors);
  return errors;
}
