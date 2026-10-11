const integerFormatter = new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 0 });
const persianDigits = "۰۱۲۳۴۵۶۷۸۹";

function localizeDigits(value) {
  return value.replace(/\d/g, (digit) => persianDigits[Number(digit)]);
}

function plainDecimal(value, decimalShift) {
  const match = /^([+-]?)(\d+)(?:\.(\d*))?(?:e([+-]?\d+))?$/i.exec(value.trim());
  if (!match) return null;

  const negative = match[1] === "-";
  const integerPart = match[2];
  const fractionPart = match[3] ?? "";
  const digits = `${integerPart}${fractionPart}`;
  const exponent = Number(match[4] ?? 0);
  if (!Number.isSafeInteger(exponent) || Math.abs(exponent + decimalShift) > 1_000 || digits.length > 1_000) return null;
  const decimalPosition = integerPart.length + exponent + decimalShift;
  if (Math.abs(decimalPosition) + digits.length > 1_000) return null;
  let integer;
  let fraction;

  if (decimalPosition <= 0) {
    integer = "0";
    fraction = `${"0".repeat(-decimalPosition)}${digits}`;
  } else if (decimalPosition >= digits.length) {
    integer = `${digits}${"0".repeat(decimalPosition - digits.length)}`;
    fraction = "";
  } else {
    integer = digits.slice(0, decimalPosition);
    fraction = digits.slice(decimalPosition);
  }

  integer = integer.replace(/^0+(?=\d)/, "");
  return { negative, integer, fraction };
}

/** Format a decimal string without converting its significant digits to a JS number. */
export function formatPersianDecimal(value, decimalShift = 0, maxFractionDigits = 2) {
  const parts = plainDecimal(String(value), decimalShift);
  if (!parts || !Number.isSafeInteger(maxFractionDigits) || maxFractionDigits < 0 || maxFractionDigits > 20) return "—";

  const fraction = parts.fraction.padEnd(maxFractionDigits + 1, "0");
  const keptFraction = fraction.slice(0, maxFractionDigits);
  const shouldRoundUp = fraction.length > maxFractionDigits && fraction[maxFractionDigits] >= "5";
  const scale = BigInt(10) ** BigInt(maxFractionDigits);
  let scaledValue = BigInt(parts.integer) * scale + BigInt(keptFraction || "0");
  if (shouldRoundUp) scaledValue += BigInt(1);

  const roundedInteger = scaledValue / scale;
  const roundedFraction = maxFractionDigits === 0
    ? ""
    : (scaledValue % scale).toString().padStart(maxFractionDigits, "0");
  const isZero = scaledValue === BigInt(0);
  const sign = parts.negative && !isZero ? "−" : "";
  const localizedInteger = integerFormatter.format(roundedInteger);
  const localizedFraction = roundedFraction ? `٫${localizeDigits(roundedFraction)}` : "";
  return `${sign}${localizedInteger}${localizedFraction}`;
}
