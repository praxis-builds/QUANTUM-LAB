// Planted legacy crypto for pq_inventory tests (never compiled).
using System.Security.Cryptography;

class Legacy {
    void Run() {
        var rsa = RSA.Create(2048);
        var md5 = MD5.Create();
        var tdes = TripleDES.Create();
        var aes = Aes.Create();
        aes.KeySize = 128;
    }
}
