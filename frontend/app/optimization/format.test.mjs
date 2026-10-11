import assert from "node:assert/strict";
import test from "node:test";
import { formatPersianDecimal } from "./format.mjs";

test("keeps integer precision beyond JavaScript's safe integer range", () => {
  assert.equal(formatPersianDecimal("9007199254740993"), "۹٬۰۰۷٬۱۹۹٬۲۵۴٬۷۴۰٬۹۹۳٫۰۰");
});

test("formats exponent notation and shifts a decimal exactly for percentages", () => {
  assert.equal(formatPersianDecimal("1.25e3"), "۱٬۲۵۰٫۰۰");
  assert.equal(formatPersianDecimal("0.1575", 2), "۱۵٫۷۵");
});

test("rounds decimal strings and avoids negative zero", () => {
  assert.equal(formatPersianDecimal("999.999"), "۱٬۰۰۰٫۰۰");
  assert.equal(formatPersianDecimal("-0.004"), "۰٫۰۰");
  assert.equal(formatPersianDecimal("not-a-number"), "—");
});
