#!/bin/python3

import os
import sys
import time
import signal
import subprocess
from argparse import ArgumentParser
from rcon.source import Client


def terminate(server):
    if server.poll() is None:
        server.terminate()
        print(f"[i] terminate process.", flush=True)
        try:
            server.wait(30)
        except subprocess.TimeoutExpired:
            server.kill()
            print(f"[i] Kill process.", flush=True)


def run(working_directory: str, command):
    # Create output files
    stdout = open(f"{working_directory}/server-stdout", "a")
    stderr = open(f"{working_directory}/server-stderr", "a")

    # Start process
    print(f"[i] Start process in {working_directory} with: {command}", flush=True)
    server = subprocess.Popen(
        command,
        cwd=working_directory,
        stdout=stdout,
        stderr=stderr,
        stdin=subprocess.PIPE,
    )
    print(f"[i] Process started.", flush=True)
    return server


def install_or_update(appid):
    process = subprocess.run(["steamcmd", "+@ShutdownOnFailedCommand", "1", "+@NoPromptForPassword", "1", "+login", "anonymous", "+app_update", args.APP_ID, "+quit"])
    if process.returncode != 0:
        print(f"[!] Error: Installation/Update failed.", flush=True)
        sys.exit(process.returncode)


def update_available(appid):
    process = subprocess.run(["steamcmd", "+@ShutdownOnFailedCommand", "1", "+@NoPromptForPassword", "1", "+login", "anonymous", "+app_info_update", "1", "+app_status", args.APP_ID, "+quit"], capture_output=True, text=True)
    if process.returncode == 0:
        for line in process.stdout.split("\n"):
            if "install state" in line:
                if "update" in line.lower():
                    return True
                break
    else:
        print(f"[!] Error: Check for Update failed.", flush=True)
        print(process.stdout)
        sys.exit(process.returncode)

    return False


# Server Process
server = None


def signal_handler(sig, frame):
    if server is not None:
        terminate(server)
    sys.exit(sig)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGABRT, signal_handler)
signal.signal(signal.SIGSEGV, signal_handler)

# Main entry point
if __name__ == "__main__":
    parser = ArgumentParser(description="Steam Game Server Handler.")
    subparsers = parser.add_subparsers(title="subcommands", dest="command")
    run_parser = subparsers.add_parser(name="run")
    run_parser.add_argument("--cwd", help=f"Working directory [default: {os.getcwd()}]", default=os.getcwd())
    run_parser.add_argument("--rcon-port", type=int, help="RCon port number.")
    run_parser.add_argument("--rcon-pw", help="RCon password.")
    run_parser.add_argument("APP_ID", help="Steam APP Identifier.")
    run_parser.add_argument("ARGS", help="Command arguments", nargs="*")
    install_parser = subparsers.add_parser(name="install")
    install_parser.add_argument("APP_ID", help="Steam APP Identifier.")
    update_parser = subparsers.add_parser(name="update")
    update_parser.add_argument("APP_ID", help="Steam APP Identifier.")
    args = parser.parse_args()

    try:
        if args.command == "install":
            install_or_update(args.APP_ID)
        elif args.command == "update":
            if update_available(args.APP_ID):
                install_or_update(args.APP_ID)
                print(f"[+] Info: App {args.APP_ID} updated.", flush=True)
            else:
                print(f"[+] Info: No update available.", flush=True)
        elif args.command == "run":
            if args.ARGS is None:
                print(f"[!] Error: No command specified.", flush=True)
                sys.exit(1)

            print(f"[+] Command: {args.ARGS}", flush=True)
            print(f"[+] Working Directory: {args.cwd}", flush=True)
            print(f"[+] Rcon Port: {args.rcon_port}", flush=True)
            print(f"[+] Rcon Password: {args.rcon_pw}", flush=True)

            rcon = None
            if args.rcon_port is not None or args.rcon_pw is not None:
                if args.rcon_port is None or args.rcon_pw is None:
                    print(f"[!] Error: RCon port or password missing.", flush=True)
                    sys.exit(1)
                    
            while True:
                if update_available(args.APP_ID):
                    if server is not None:
                        if rcon is not None:
                            restart = 5
                            while restart > 0:
                                print(f"[+] Announce restart in {restart} minutes.", flush=True)
                                rcon.run('announcerestart', str(restart))
                                restart = restart - 1
                                time.sleep(60)
                            rcon.close()
                            rcon = None
                        print("[+] Shutdown server.", flush=True)
                        terminate(server)
                        server = None

                    print("[+] Update server.", flush=True)
                    install_or_update(args.APP_ID)
                
                if server is None:
                    print("[+] Start server.", flush=True)
                    server = run(args.cwd, args.ARGS)
                    time.sleep(60)
                    if args.rcon_port is not None or args.rcon_pw is not None:
                        rcon = Client('127.0.0.1', args.rcon_port, passwd=args.rcon_pw)
                        rcon.connect()
                        rcon.login(args.rcon_pw)

                time.sleep(2 * 60)
        else:
            print(f"[!] Error: No subcommand specified.", flush=True)
    except Exception as e:
        print(f"[!] Error: {e}", flush=True)
        if server is not None:
            terminate(server)
        sys.exit(1)
