# Prusa Link API

## API Version

```shell
curl  'http://172.32.1.123/api/version' \
 -H "X-Api-Key: w9d5PVd7FN6mC3o"
```

```json
{
  "api": "2.0.0",
  "server": "2.1.2",
  "nozzle_diameter": 0.60,
  "text": "PrusaLink",
  "hostname": "",
  "capabilities": {
    "upload-by-put": true
  }
}
```

## Printer Status

```shell
curl  'http://172.32.1.123/api/v1/status' \
 -H "X-Api-Key: w9d5PVd7FN6mC3o"
```

### Idle

```json
{
  "storage": {
    "path": "/usb/",
    "name": "usb",
    "read_only": false
  },
  "printer": {
    "state": "IDLE",
    "temp_bed": 23.8,
    "target_bed": 0.0,
    "temp_nozzle": 24.0,
    "target_nozzle": 0.0,
    "axis_z": 0.0,
    "axis_x": -8.0,
    "axis_y": -9.0,
    "flow": 100,
    "speed": 100,
    "fan_hotend": 0,
    "fan_print": 0,
    "status_connect": {
      "ok": true,
      "message": "OK"
    }
  }
}
```

### Printing

```json
{
  "job": {
    "id": 4,
    "progress": 0.00,
    "time_remaining": 0,
    "time_printing": 258
  },
  "storage": {
    "path": "/usb/",
    "name": "usb",
    "read_only": false
  },
  "printer": {
    "state": "PRINTING",
    "temp_bed": 60.1,
    "target_bed": 60.0,
    "temp_nozzle": 199.0,
    "target_nozzle": 200.0,
    "axis_z": 0.3,
    "flow": 100,
    "speed": 100,
    "fan_hotend": 2614,
    "fan_print": 0,
    "status_connect": {
      "ok": true,
      "message": "OK"
    }
  }
}
```

## Finished

```json
{
  "storage": {
    "path": "/usb/",
    "name": "usb",
    "read_only": false
  },
  "printer": {
    "state": "FINISHED",
    "temp_bed": 56.9,
    "target_bed": 0.0,
    "temp_nozzle": 174.0,
    "target_nozzle": 0.0,
    "axis_z": 30.0,
    "axis_x": 2.0,
    "axis_y": 351.0,
    "flow": 100,
    "speed": 100,
    "fan_hotend": 4049,
    "fan_print": 0,
    "status_connect": {
      "ok": true,
      "message": "OK"
    }
  }
}
```

## Stopped

```json
{
  "storage": {
    "path": "/usb/",
    "name": "usb",
    "read_only": false
  },
  "printer": {
    "state": "STOPPED",
    "temp_bed": 50.8,
    "target_bed": 0.0,
    "temp_nozzle": 73.0,
    "target_nozzle": 0.0,
    "axis_z": 70.0,
    "axis_x": 2.0,
    "axis_y": 351.0,
    "flow": 100,
    "speed": 100,
    "fan_hotend": 2659,
    "fan_print": 0,
    "status_connect": {
      "ok": true,
      "message": "OK"
    }
  }
}
```

## Latest Job

```shell
curl  'http://172.32.1.123/api/v1/job' \
 -H "X-Api-Key: w9d5PVd7FN6mC3o"
```

Download Preview Image

```shell
curl  -O 'http://172.32.1.123/thumb/s/usb/ASSEM1~1.BGC' \
  -H "X-Api-Key: w9d5PVd7FN6mC3o"
```

Download Gcode

```shell
curl  -O 'http://172.32.1.123/usb/P3_GOL~1.BGC' \
  -H "X-Api-Key: w9d5PVd7FN6mC3o"
```

```json
{
  "id": 4,
  "state": "PRINTING",
  "progress": 0.00,
  "time_remaining": 0,
  "time_printing": 225,
  "file": {
    "refs": {
      "icon": "/thumb/s/usb/A~1.GCO",
      "thumbnail": "/thumb/l/usb/A~1.GCO",
      "download": "/usb/A~1.GCO"
    },
    "name": "A~1.GCO",
    "display_name": "A.gcode",
    "path": "/usb",
    "size": 60337,
    "m_timestamp": 1705971622
  }
}
```

### Response After Stopping Job

```json
{
  "id": 14,
  "state": "PRINTING",
  "progress": 0.00,
  "time_remaining": 0,
  "time_printing": 19,
  "file": {
    "refs": {
      "icon": "/thumb/s/usb/GOOGLE~1.GCO",
      "thumbnail": "/thumb/l/usb/GOOGLE~1.GCO",
      "download": "/usb/GOOGLE~1.GCO"
    },
    "name": "GOOGLE~1.GCO",
    "display_name": "google-oauth2-114001599292160974567-1705761632.gcode",
    "path": "/usb"
  }
}
```

## File Presence

```shell
curl -X HEAD 'http://172.32.1.181/api/v1/files/usb/A.gcode' \
--header 'X-Api-Key: w9d5PVd7FN6mC3o'
```

## Upload File

```shell
curl --location --request PUT 'http://172.32.1.181/api/v1/files/usb/A.gcode' \
--header 'X-Api-Key: w9d5PVd7FN6mC3o' \
--header 'Print-After-Upload: 0' \
--header 'Content-Type: application/octet-stream' \
--data '@/Users/jichengzhi/Downloads/A.gcode'
```

```json
{
  "name": "A~1.GCO",
  "ro": false,
  "type": "PRINT_FILE",
  "m_timestamp": 1705975875,
  "size": 58350,
  "refs": {
    "icon": "/thumb/s/usb/A~1.GCO",
    "thumbnail": "/thumb/l/usb/A~1.GCO",
    "download": "/usb/A~1.GCO"
  },
  "display_name": "A.gcode"
}
```

## Delete File

```shell
curl -X DELETE 'http://172.32.1.181/api/v1/files/usb/A.gcode' \
--header 'X-Api-Key: w9d5PVd7FN6mC3o'
```

## Stop Job

```shell
curl -X DELETE 'http://172.32.1.181/api/v1/job' \
 -H "X-Api-Key: w9d5PVd7FN6mC3o"
```
