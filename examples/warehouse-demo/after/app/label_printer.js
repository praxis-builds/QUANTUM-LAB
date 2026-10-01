// Label printing service for the fictional Northwind Warehouse (demo code, never run). Migrated: wave 1.
const crypto = require("crypto");

function labelId(text) {
  return crypto.createHash("sha256").update(text).digest("hex");
}

function sealPrinterJob(job, key32, iv12) {
  const cipher = crypto.createCipheriv("aes-256-gcm", key32, iv12);
  return Buffer.concat([cipher.update(job), cipher.final(), cipher.getAuthTag()]);
}

module.exports = { labelId, sealPrinterJob };
