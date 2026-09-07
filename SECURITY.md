# Security Policy 🔒 (HYDRA-UMC-SUITE)

## Reporting a Vulnerability

For the desktop suite, we are concerned with **Network Discovery spoofing** and **Unauthorized Local File Access**.

Report issues privately to `electrohobby3d@gmail.com`.

### Focus Areas
- Man-in-the-middle (MITM) attacks on the WebSocket link.
- Malicious server payloads causing UI crashes or RCE.

## Credentials

Discovered servers are not trusted authorization sources. The suite requires
operator-entered credentials for every new connection and does not assume a
reusable default administrator account.
