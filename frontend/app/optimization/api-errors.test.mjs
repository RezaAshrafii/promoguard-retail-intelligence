import assert from "node:assert/strict";
import test from "node:test";
import { formatApiValidationErrors } from "./api-errors.mjs";

test("shows Persian field labels and translates Pydantic missing errors", () => {
  const messages = formatApiValidationErrors([
    { loc: ["body", "policy", "minimum_incremental_profit"], type: "missing" },
  ]);
  assert.deepEqual(messages, ["سیاست حداقل سود ← حداقل سود افزوده: این فیلد وارد نشده است."]);
});

test("identifies a scenario index and reports an invalid date", () => {
  const messages = formatApiValidationErrors([
    { loc: ["body", "optimization", "scenarios", 1, "start_date"], type: "date_parsing" },
  ]);
  assert.deepEqual(messages, ["تنظیمات کمپین ← سناریوها ← سناریوی ۲ ← تاریخ شروع: تاریخ معتبر نیست؛ قالب YYYY-MM-DD را وارد کن."]);
});

test("limits long validation lists and provides a safe fallback for unknown errors", () => {
  const issues = Array.from({ length: 10 }, (_, index) => ({ loc: ["body", `field_${index}`], type: "unknown_error" }));
  const messages = formatApiValidationErrors(issues, 2);
  assert.equal(messages.length, 3);
  assert.match(messages[0], /با قرارداد ورودی سازگار نیست/);
  assert.equal(messages[2], "و ۸ مورد دیگر؛ خطاها را از ابتدای فهرست اصلاح کن.");
  assert.deepEqual(formatApiValidationErrors("server error"), []);
});
