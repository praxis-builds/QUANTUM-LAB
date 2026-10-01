# Lesson 32: hybrid key exchange (X25519 + ML-KEM-768)

> **Educational, not production.** No authentication, no TLS key schedule, no review. Use your TLS library's built-in hybrid groups instead.

## The idea
ML-KEM is new. Its security rests on lattice problems studied for far less time than elliptic curves, and a surprise attack on it, or a bug in an implementation, cannot be ruled out. X25519 is well studied but falls to Shor. A **hybrid** key exchange runs both at once and feeds both shared secrets into a key derivation function (here **HKDF**). An attacker must break **both** to learn the key.

That is what browsers deploy today. Chrome switched its default TLS key exchange to the hybrid **X25519MLKEM768** (codepoint 0x11EC) in Chrome 131 (November 2024), replacing an earlier hybrid with pre-standard Kyber. The IETF's design for hybrid key exchange in TLS 1.3 aims to provide "security even if a way is found to defeat the encryption for all but one of the component algorithms".

## Predict first
1. How many bytes does each side send, compared with about 32 for X25519 alone?
2. An attacker with a quantum computer recovers the X25519 secret. Does she get the session key?
3. Why bind the key to the transcript (everything sent) rather than just the two secrets?

## How to run

    .venv/bin/python lessons/32_hybrid_key_exchange.py

It prints two labelled steps in under a second (needs the `[pqc]` extra; otherwise it prints the reason and stops).

## What you should see, and why
Answers are below.

## Spoiler
1. Client to server: 1,216 bytes (a 32-byte X25519 share and the 1,184-byte ML-KEM-768 public key). Server to client: 1,120 bytes (a 32-byte share and the 1,088-byte ciphertext). That fits in one handshake round trip, at about 35 times the size of X25519 alone.
2. **No.** With the X25519 secret but only a guess for the ML-KEM secret, HKDF gives a different key. The reverse also fails: a hypothetical lattice break that reveals the ML-KEM secret, without the X25519 secret. Only knowing both gives the session key. That is the whole argument for hybrid during the transition.
3. Binding the key to the transcript ties it to exactly these messages, so a key derived from altered messages comes out different. Real protocols (TLS 1.3) do this through their key schedule and also **authenticate** the handshake with signatures. This demo does neither properly: anyone in the middle could run it with each side separately, which is why it is labelled educational.

**Sources (checked on 2026-09-30).**
- D. Adrian, D. Benjamin, B. Beck, D. O'Brien (Chrome team), "A new path for Kyber on the web", Google Online Security Blog, 13 September 2024 ([link](https://security.googleblog.com/2024/09/a-new-path-for-kyber-on-web.html)): Chrome switches from Kyber to ML-KEM, with key share prediction for the codepoint 0x11EC (ML-KEM768+X25519). The Chrome 131 / November 2024 release is reported consistently by several sources; the blog post itself announces the switch.
- IETF, "Hybrid key exchange in TLS 1.3", published as RFC 9954 in July 2026 (from draft-ietf-tls-hybrid-design; [datatracker](https://datatracker.ietf.org/doc/draft-ietf-tls-hybrid-design/)). The quote above is from its abstract. It also names retroactive decryption ("harvest-now-decrypt-later") as the reason to adopt early.

**Classical baseline.** X25519 alone: 32 bytes each way, but recorded handshakes become readable once Shor is practical (Lesson 30).

**What this does NOT show.** The exact secret combination and key schedule TLS uses for X25519MLKEM768 (here: HKDF-SHA256 over the ML-KEM secret followed by the X25519 secret, with the transcript hash in `info`), or authentication. Signatures are Lesson 33.
