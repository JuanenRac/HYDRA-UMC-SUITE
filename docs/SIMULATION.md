# Simulation bench

Runs the real network client, the sign-in and the logic of the panels against fake servers only: a small HTTP server and a WebSocket server on this machine, with no robot, no real HYDRA-UMC-SERVER and no network beyond localhost. The workflow `simulation.yml` runs the verifiers below with the interface headless (`QT_QPA_PLATFORM=offscreen`), and a second job runs every verifier under coverage and prints the coverage of the program.

Scenarios:

- answers that lie: a global STOP never raises whatever a 200 answer carries, a server without the route or one that rate limits gets the stop robot by robot, a WebSocket message of the wrong shape never replaces the state with a broken tree, and the messages for refused writes read differently for 400, 401, 403, 409 and 5xx (`tests/verify_hostile_server_answers.py`);
- the session: a scan result with no credentials is never sent a login, a rejected login is not retried, an expired token is renewed once and the request repeated, a warning means "not applied" and is rolled back, the token travels as a subprotocol and never in the address (`tests/verify_session_and_errors.py`, `tests/verify_session_module.py`);
- a connection that is cut: the global STOP asks again once when nobody answers and says "not confirmed" when nothing confirmed it (`tests/verify_stop_all.py`); a settings answer that is cut in the middle of its body fails the read with a network error and the next read works; a server that is off is retried without giving up, and when it comes up, drops the connection and comes back, the client reconnects by itself, keeps the session without a new login, ignores the text that is not JSON and the message that is not an object, and shows the state of the connection that survives (`tests/verify_session_and_errors.py`);
- the access limits, the bridges, the reservations, the conditional audit, damaged panel data and downloads, the live updates, the MJPEG stream, the one-time code, the discovery of servers and the check of updates with the signature vectors (the other verifiers of the workflow).

The evidence of this project is `simulator`: it says nothing about a real controller, a real robot, a real network or the real server. Every physical step stays in `docs/BENCH_TESTS.md`.

Physical tests still pending:

- the SUITE on a PC and a running HYDRA-UMC-SERVER on the CM5: stop the server for ten seconds, then start it; expected: the header shows "disconnected" while it is off and "connected" again by itself, the robots show the state the server holds after it returns, and no password is asked again;
- the global STOP with the server unreachable and then reachable (pull the cable of the CM5, press STOP, plug it in, press STOP); expected: the first STOP shows the red "not confirmed" message and the second confirms every robot.
