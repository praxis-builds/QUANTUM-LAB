"""pq_tls: does a website already use post-quantum (hybrid) key exchange?

Sends one TLS 1.3 ClientHello that offers X25519MLKEM768 (RFC 10024) and reads which group the
server picks. The handshake is never completed. See docs/pq-tls.md.
"""

__version__ = "0.1.0"
