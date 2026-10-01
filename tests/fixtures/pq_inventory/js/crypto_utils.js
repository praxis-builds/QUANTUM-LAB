// Planted legacy crypto for pq_inventory tests (never executed).
const crypto = require("crypto");

// md5 was used here once (a comment: must NOT be reported)
const { publicKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 1024 });
const digest = crypto.createHash("sha1").update("x").digest("hex");
const modern = crypto.createCipheriv("aes-256-gcm", key32, iv);
const legacy = crypto.createCipheriv("des-ede3-cbc", key24, iv8);
module.exports = { publicKey, digest, modern, legacy };
