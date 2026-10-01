// Planted legacy crypto for pq_inventory tests (never executed).
import java.security.*;
import javax.crypto.Cipher;

public class Legacy {
    void run() throws Exception {
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
        kpg.initialize(2048);
        MessageDigest md = MessageDigest.getInstance("MD5");
        Cipher c = Cipher.getInstance("DESede/CBC/PKCS5Padding");
        Signature s = Signature.getInstance("SHA256withECDSA");
    }
}
