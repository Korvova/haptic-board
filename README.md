# haptic-board

ESP32 haptic prototype for mouse-movement lessons. The board drives vibration
motors under the hand and on the mouse-click fingers, while browser tools record
and replay cursor movement, clicks, right-click context menus, drag-and-drop, and
screen/video lessons.

## Hardware

Target board: ESP32 Dev Module (`esp32dev`) with Arduino framework.

Motor map used by the firmware:

| Signal | ESP32 pin | Meaning |
| --- | ---: | --- |
| `left` | GPIO21 | left side under hand |
| `center` | GPIO22 | center under hand |
| `right` | GPIO23 | right side under hand |
| `top` | GPIO19 | top under hand |
| `bottom` | GPIO18 | bottom under hand |
| `topLeft` | GPIO5 | upper-left diagonal |
| `topRight` | GPIO17 | upper-right diagonal |
| `leftClick` | GPIO25 | left mouse click / index finger |
| `rightClick` | GPIO33 | right mouse click |

Use MOSFET/transistor drivers and a motor power rail. Do not power vibration
motors directly from ESP32 GPIO pins. Tie motor power ground and ESP32 ground
together.

## Firmware

Build:

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run
```

Upload to the ESP32 on `COM4`:

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run --target upload --upload-port COM4
```

The firmware listens on Serial at `115200` baud.

Serial protocol:

```text
V left center right top bottom topLeft topRight leftClick rightClick
S
```

All `V` values are PWM levels from `0` to `255`. `S` stops all motors. The
firmware also stops all motors automatically if commands stop arriving for
300 ms.

For compatibility while prototyping, the firmware still accepts older shorter
forms with 3, 5, 7, or 8 values.

## Browser tools

Serve the project directory from localhost:

```powershell
& "$env:USERPROFILE\.platformio\penv\Scripts\python.exe" -m http.server 8765
```

Open the tools in Chrome or Edge:

```text
http://localhost:8765/tools/haptic_mouse_web.html
http://localhost:8765/tools/interactive_lesson_lab.html
```

### `haptic_mouse_web.html`

Manual haptic test surface.

- Connects to ESP32 with Web Serial.
- Converts mouse movement into haptic direction patterns.
- Supports horizontal, vertical, diagonal, click, right-click, and flow-style
  motion patterns.
- Includes a `Play 2m Lesson` demo for quick immersion testing.

### `interactive_lesson_lab.html`

Interactive recording and playback lab.

It contains a fake app surface with:

- buttons
- right-click context menu
- drag-and-drop tiles
- cursor playback
- left/right click haptics
- screen capture and lesson export

Basic recording:

1. Click `Connect ESP32`.
2. Click `Record`.
3. Move, click, right-click, and drag items inside the lab.
4. Click `Stop Recording`.
5. Click `Play Recording`.

Screen/video lesson recording:

1. Click `Connect ESP32`.
2. Click `Start Capture + Record`.
3. In Chrome, choose the tab/window/screen to capture.
4. Perform the lesson actions.
5. Click `Stop Capture`.
6. Download `lesson.json` and `lesson.webm`.

Loading a lesson:

1. Click `Load JSON` and select `lesson.json`.
2. Click `Load Video` and select `lesson.webm`.
3. Click `Play Loaded Lesson`.

During loaded video playback, the page does not draw duplicate context menus or
click rings over the video; it only sends synchronized haptic signals.

## Lesson JSON

The exported JSON is a manifest:

```json
{
  "version": 1,
  "createdAt": "2026-05-23T00:00:00.000Z",
  "durationMs": 12000,
  "video": "lesson.webm",
  "viewport": { "width": 1280, "height": 720 },
  "events": [
    { "t": 0, "type": "move", "x": 0.18, "y": 0.28 },
    { "t": 900, "type": "click", "x": 0.18, "y": 0.28, "button": 0 },
    { "t": 1800, "type": "context", "x": 0.56, "y": 0.28 }
  ]
}
```

Coordinates are normalized from `0` to `1` inside the lab workspace. Haptics are
generated from events during playback, so patterns can be tuned without changing
the saved lesson file.

## Notes

- Web Serial requires Chrome or Edge and a localhost/secure context.
- If upload fails with `COM4` busy, disconnect the browser from ESP32 or close
  the tab before flashing.
- `GPIO35` is input-only on ESP32 and cannot drive a vibration motor; use output
  pins such as `GPIO25` or `GPIO33` for click motors.
