#!/bin/python3

import os
import sys
import json
import time
import socket
import shutil
import signal
import subprocess
import multiprocessing as mp
from datetime import datetime
from argparse import ArgumentParser
from rcon.source import Client


def terminate(server, game):
    game = game if game else "i"
    if server.poll() is None:
        server.terminate()
        print(f"[{game}] terminate process.", flush=True)
        try:
            server.wait(30)
        except subprocess.TimeoutExpired:
            server.kill()
            print(f"[{game}] Kill process.", flush=True)


def run(working_directory: str, command, environment, game):
    game = game if game else "i"

    # Create output files
    stdout = open(f"{working_directory}/server-stdout", "a")
    stderr = open(f"{working_directory}/server-stderr", "a")
    
    for e in environment:
        environment[e] = str(environment[e])

    env = os.environ.copy()
    env = { **env, **environment }

    # Start process
    print(f"[{game}] Start process in {working_directory} with: {command}", flush=True)
    server = subprocess.Popen(
        command,
        env=env,
        cwd=working_directory,
        stdout=stdout,
        stderr=stderr,
        stdin=subprocess.PIPE,
    )
    print(f"[{game}] Process started.", flush=True)
    return server

def install_or_update(appid, game):
    game = game if game else "!"
    process = subprocess.run(["steamcmd", "+@ShutdownOnFailedCommand", "1", "+@NoPromptForPassword", "1", "+login", "anonymous", "+app_update", str(appid), "+quit"])
    if process.returncode != 0:
        print(f"[{game}] Error: Installation/Update failed.", flush=True)
        sys.exit(process.returncode)

def update_available(appid, game, force):
    if force:
        return True
    game = game if game else "!"
    process = subprocess.run(["steamcmd", "+@ShutdownOnFailedCommand", "1", "+@NoPromptForPassword", "1", "+login", "anonymous", "+app_info_update", "1", "+app_status", str(appid), "+quit"], capture_output=True, text=True)
    if process.returncode == 0:
        for line in process.stdout.split("\n"):
            if "install state" in line:
                if "update" in line.lower():
                    print(f"[{game}] Update available.", flush=True)
                    return True
                break
    else:
        print(f"[{game}] Error: Check for Update failed.", flush=True)
        for l in process.stdout.split('\n'):
            print(f"[{game}] {l}")
        sys.exit(process.returncode)

    print(f"[{game}] No update available.", flush=True)
    return False

run_game_servers = True

def signal_handler(sig, frame):
    global run_game_servers
    run_game_servers = False
    print("[!] Signal handler. Terminating now.", file = sys.stderr, flush=True)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGABRT, signal_handler)
signal.signal(signal.SIGSEGV, signal_handler)

def sleep(secs):
    global run_game_servers
    for i in range(1, secs):
        if not run_game_servers:
            break
        time.sleep(1)
    return run_game_servers

def shutdown_server(server, game, rcon):
    global run_game_servers

    if rcon is not None:
        restart = 5 if run_game_servers else 0

        # Announce restart each minute
        while run_game_servers and restart > 0:
            print(f"[{game}] Announce restart in {restart} minutes.", flush=True)
            rcon.run('announcerestart', str(restart))
            sleep(60)
            restart = restart - 1

        # Announce forced shutdown
        if not run_game_servers:
            print(f"[{game}] Announce forced shutdown.", flush=True)
            rcon.run('announce', 'Server will shutdown immediately.')
            time.sleep(30)
        
        # Close rcon
        rcon.close()
        rcon = None

    # Terminate server
    print(f"[{game}] Shutdown server.", flush=True)
    terminate(server, game)

def backup_required(location):
    date = datetime.now()
    if date.hour < 3:
        return

    date_str = date.strftime('%Y-%m-%d')
    backup_path = os.path.join(location, date_str)
    if os.path.exists(backup_path):
        return None
    else:
        return backup_path

def create_backup(game, location, data):
    backup_path = backup_required(location)
    if backup_path is not None:
        print(f"[{game}] Creating backup.", flush=True)
        os.makedirs(backup_path, exist_ok=True)
        for d in data:
            if os.path.isdir(d):
                shutil.copytree(d, os.path.join(backup_path, os.path.basename(d)))
            else:
                shutil.copyfile(d, os.path.join(backup_path, os.path.basename(d)))

def run_game(game, app_id, command, working_directory, environment, rcon_port, rcon_pw, backup):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    global run_game_servers

    print(f"[{game}] Application ID: {app_id}", flush=True)
    print(f"[{game}] Command: {" ".join(command)}", flush=True)
    print(f"[{game}] Working Directory: {working_directory}", flush=True)
    print(f"[{game}] Environment: {environment}", flush=True)
    print(f"[{game}] Rcon Port: {rcon_port}", flush=True)
    print(f"[{game}] Rcon Password: {rcon_pw}", flush=True)

    rcon = None
    if rcon_port is not None or rcon_pw is not None:
        if rcon_port is None or rcon_pw is None:
            print(f"[{game}] Error: RCon port or password missing.", flush=True)
            run_game_servers = False

    create_backup(game, backup["location"], backup["data"])
            
    server = None
    force = True
    while run_game_servers:
        to_update = update_available(app_id, game, force)
        force = False
        to_backup = backup_required(backup["location"])
        if to_update or to_backup:
            if server is not None:
                shutdown_server(server, game, rcon)
                server = None

            if run_game_servers and to_backup:
                create_backup(game, backup["location"], backup["data"])
            
            if run_game_servers and to_update:
                print(f"[{game}] Update server.", flush=True)
                install_or_update(app_id, game)
        
        if server is None:
            print(f"[{game}] Start server.", flush=True)
            server = run(working_directory, command, environment, game)
            time.sleep(60)
            if rcon_port is not None or rcon_pw is not None:
                rcon = Client('127.0.0.1', rcon_port, passwd=rcon_pw)
                rcon.connect()
                rcon.login(rcon_pw)
        
        sleep(2*60)
    if server is not None:
        shutdown_server(server, game, rcon)

    create_backup(game, backup["location"], backup["data"])
    print(f"[{game}] Game process finished.", flush=True)

# Main entry point
if __name__ == "__main__":
    parser = ArgumentParser(description="Steam Game Server Handler.")
    subparsers = parser.add_subparsers(title="subcommands", dest="command")
    run_parser = subparsers.add_parser(name="run")
    run_parser.add_argument("CONFIG", help="Path to the configuration JSON file.")
    install_parser = subparsers.add_parser(name="install")
    install_parser.add_argument("APP_ID", help="Steam APP Identifier.")
    update_parser = subparsers.add_parser(name="update")
    update_parser.add_argument("-f", "--force", help="Force update.")
    update_parser.add_argument("APP_ID", help="Steam APP Identifier.")
    args = parser.parse_args()

    try:
        if args.command == "install":
            install_or_update(args.APP_ID, None)
        elif args.command == "update":
            if update_available(args.APP_ID, None, args.force):
                install_or_update(args.APP_ID, None)
                print(f"[+] Info: App {args.APP_ID} updated.", flush=True)
            else:
                print(f"[+] Info: No update available.", flush=True)
        elif args.command == "run":
            config = dict()
            with open(args.CONFIG, 'r') as fp:
                config = json.load(fp)

            game_servers = []
            for game in config:
                if config[game]["command"] is None or len(config[game]["command"]) == 0:
                    print(f"[{game}] Error: No command specified for {game}.", flush=True)
                    sys.exit(1)
                if "rcon" in config[game] and ("port" not in config[game]["rcon"] or "password" not in config[game]["rcon"]):
                    print(f"[{game}] Error: Invalid RCon configuration for {game}.", flush=True)
                    sys.exit(1)
                for param in ["app_id", "command", "backup"]:
                    if param not in config[game]:
                        print(f"[{game}] Error: Missing parameter {param} for {game}.", flush=True)
                        sys.exit(1)
                if not "location" in config[game]["backup"] or not "data" in config[game]["backup"]:
                    print(f"[{game}] Error: Missing parameter 'location' or 'data' in 'backup' for {game}.", flush=True)
                    sys.exit(1)
                app_id = config[game]["app_id"] 
                command = config[game]["command"]
                environment = config[game]["environment"] if "environment" in config[game] else dict()
                working_directory = config[game]["working_directory"] if "working_directory" in config[game] else "."
                rcon_port = None if "rcon" not in config[game] or "port" not in config[game]["rcon"] else config[game]["rcon"]["port"]
                rcon_pw = None if "rcon" not in config[game] or "password" not in config[game]["rcon"] else config[game]["rcon"]["password"]
                backup = config[game]["backup"]
                game_servers.append((game, app_id, command, working_directory, environment, rcon_port, rcon_pw, backup))

            workers = []
            for game in game_servers:
                tmp = mp.Process(target=run_game, args=game)
                tmp.start()
                workers.append(tmp)
            
            for worker in workers:
                worker.join()
        else:
            print(f"[!] Error: No subcommand specified.", flush=True)
    except Exception as e:
        print(f"[!] Error: {e}", flush=True)
            
