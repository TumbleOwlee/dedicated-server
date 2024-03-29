# Dedicated Server Maintenance

This repository contains a simple Python script that can be used to install, run and update a dedicated game server. To update the server, it utilizes the SteamCMD tool.

To install, run or update a dedicated game server, you will have to retrieve the game app identifier used by Steam. In case you already have to identifier and the SteamCMD tool is in your system path, you can install the server like this.

```python
./run_server.py install <APPID>
```

If you want to update the server, utilize the `update` subcommand.

```python
./run_server.py update <APPID>
```

The most important subcommand is `run`. Using `run` the provided commandline to start the dedicated server will be executed and Steam will be checked for available updates every 5 minutes. If an update is available, the server will be terminated, updated and restarted afterwards. If Rcon is supported and the port and password are provided, it will also transmit the `announcerestart` command 5 minutes prior to the shutdown to inform all active players.

E.g. a bat file for the V Rising dedicated server could look like this.
```bat
@echo off
set SteamAppId=1604030
python <PATH>\run_server.py run --cwd C:\SteamCMD\steamapps\common\VRisingDedicatedServer --rcon-port <PORT> --rcon-pw <PASSWORD> 1829350 -- C:\SteamCMD\steamapps\common\VRisingDedicatedServer\VRisingServer.exe -persistentDataPath <DATAPATH> -serverName <NAME> -saveName <SAVE> -logFile ".\logs\VRisingServer.log"
```
