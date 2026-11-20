# The phone as physical senses (first-principles names, agreed 2026-11-19)

Think of each sensor by what physically happens inside it, not by its intended job.

## Senses (listen)
| Physical quantity | Usual name | First-principles name | Rate on this Pixel | Also picks up |
|---|---|---|---|---|
| Air pressure | Microphones (3) | Fast air-pressure sensors | 48 000/s | echoes, any vibration of the air, electronics whine |
| Air pressure | Barometer (SPA18001) | Slow air-pressure sensor | 25/s | height (~12 Pa/m), weather, doors, gusts, infrasound |
| Force / inertia | Accelerometer (TDK ICM45631) | Push sensor (tiny weight on springs, read capacitively) | up to 400/s | gravity -> tilt, bumps, surface vibration, footsteps, heartbeat on a chest, loud sound (weakly) |
| Force / inertia | Gyroscope (same TDK chip) | Twist sensor (tiny vibrating fork) | up to 400/s | strong vibration, loud nearby sound (speech research: "Gyrophone") |
| Magnetic field | Magnetometer (MEMSIC MMC5616) | Magnetic field sensor | 100/s | Earth's field (north), nearby steel (screws, pipes, radiators), currents (wiring), magnets; short range (falls with distance cubed) |
| Radio | Wi-Fi (RTT + Aware supported) | Radio stopwatch and strength meter | per measurement | distance to RTT routers (~1-2 m), phone-to-phone distance |
| Light | Ambient light / colour (TMD3743) | Fast light meter (front) | up to 240/s | flicker (100-120 Hz lights), shadows, window direction |
| Light | Rear light (VD628X) | Back-side light meter | up to 62/s | same, other side |
| Light | Proximity (TMD3743, infrared) | Infrared bounce sensor | up to 120/s | only a few cm; apps usually get near/far only |
| Light | Cameras | Light image grids | 30/s | millions of light meters |
| Heat | Chip temperatures (gyro chip, barometer chip) | Chip thermometers | 25-50/s | phone's inside temperature: follows the room slowly, runs warm with use |

## Emitters (act)
| Usual name | First-principles name | Pairs with |
|---|---|---|
| Speaker | Air pusher | microphones (sonar) |
| Vibration motor | Shaker | push sensor (surface stiffness) |
| Screen and flash | Light emitters | light meters |
| Infrared emitter (in the proximity sensor) | Invisible light pulser | infrared bounce sensor |
| Wi-Fi radio | Radio pinger | radio stopwatch |

Most tricks come from crossing them: a twist sensor hearing sound, a slow pressure sensor hearing doors, a light meter
acting as a compass, the speaker plus mics as sonar.
