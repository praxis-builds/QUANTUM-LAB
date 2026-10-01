// Label printing service for the fictional Northwind Warehouse (demo code, never run).
const crypto = require("crypto");

function labelId(text) {
  return crypto.createHash("md5").update(text).digest("hex");
}

function sealPrinterJob(job, key24, iv8) {
  const cipher = crypto.createCipheriv("des-ede3-cbc", key24, iv8);
  return Buffer.concat([cipher.update(job), cipher.final()]);
}

module.exports = { labelId, sealPrinterJob };
