// Supplier EDI feed for the fictional Northwind Warehouse (demo code, never compiled).
import java.security.*;

public class SupplierFeed {
    KeyPair signingKeys() throws Exception {
        KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");
        kpg.initialize(2048);
        return kpg.generateKeyPair();
    }

    byte[] fingerprint(byte[] invoice) throws Exception {
        return MessageDigest.getInstance("SHA-1").digest(invoice);
    }

    Signature shipmentSignature() throws Exception {
        return Signature.getInstance("SHA256withECDSA");
    }
}
