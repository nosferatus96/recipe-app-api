import asyncio
import binascii
import logging
import ssl
import subprocess
import traceback
import typing
import time
import zBlaze
import TCP.HaltSearch
import discord
from datetime import datetime, timezone
import sys
import os
import psutil
from os import path
from discord.ext import commands, tasks
from discord.ext.commands import Bot
from discord import app_commands
import json
import configparser
import sqlite3
import requests
import VPNAPI
from datetime import datetime

guild = discord.Object(id=939915155792355338)
intents = discord.Intents.all()
cParse = configparser.RawConfigParser()
cFilePathAuth = path.join((path.abspath(path.dirname(sys.argv[0]))), "Authentication.txt")
DBPath = r'C:\Users\jonat\OneDrive\Bureau\Private Database\TCP\CheaterDatabase.txt'
cParse.read(cFilePathAuth)
botToken = cParse.get("BotConfig", "botToken")
intents.message_content = True
client: Bot = commands.Bot(command_prefix='$', intents=intents)
client.remove_command("help")
client.remove_command("invite")


class UserInput:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def swap32(dword, Len):
    return int.from_bytes(dword.to_bytes(Len, byteorder='little'), byteorder='big', signed=False)


def modify_line(line, User, PID):
    if User in line:
        parts = line.split(", ")
        if "0000000000000" in str(parts[1].strip()):
            parts[1] = str(str(PID) + "\n")
            return ", ".join(parts)
    return line


async def restart_if_memory_exceeds(threshold):
    process = psutil.Process(os.getpid())
    memory_usage = process.memory_info().rss
    print("NOTICE: Current usage is " + str(memory_usage / (1024 ** 3)))
    if memory_usage > threshold:
        AutoChannel = client.get_channel(1242348944764174396)
        print("NOTICE: Memory threshold exceeded. Restarting script...")
        embed = discord.Embed(color=16711680, description="``" + "ERROR: Memory Threshold exceeded 2048M, Restarting" + "``")
        await AutoChannel.send(embed=embed)
        await reboot()


def EditAuthFile(Tag, Update, Edit, Folder):
    if not Edit:
        cParse.read(cFilePathAuth)
        EASavedInfo = [cParse.get(Folder, str(Tag))]
        return EASavedInfo[0]
    if Edit:
        with open(cFilePathAuth, 'r') as file:
            lines = file.readlines()
            file.close()
        modified_lines = []
        Count = 0
        for line in lines:
            Count = Count + 1
            parts = line.strip().split('=')
            if str(Tag) in str(parts[0].strip()):
                modified_lines.append(Tag + " = " + Update + "\n")
            else:
                modified_lines.append(line)
        with open(cFilePathAuth, 'w') as file:
            file.writelines(modified_lines)
            file.close()
        return


async def CleanDatabase():
    conn = sqlite3.connect('PlayerDatabase.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players")
    Database = cursor.fetchall()
    for Players in Database:
        PlayerIDs = Players[2]
        if "," in PlayerIDs:
            PlayerIDs = PlayerIDs.split(",")
            if len(PlayerIDs) > 1:
                print("Interesting")

        MACAddresses = Players[3]
        if "," in MACAddresses:
            MACAddresses = MACAddresses.split(",")
            if len(MACAddresses) > 20:
                print("Might Have to Filter")

        PublicIPAddresses = Players[4]
        if "," in PublicIPAddresses:
            PublicIPAddresses = PublicIPAddresses.split(",")
            if len(PublicIPAddresses) > 20:
                print("Might Have to Filter")
        if isinstance(PublicIPAddresses, str):
            PublicIPAddresses = [PublicIPAddresses]
        for Instances in PublicIPAddresses:
            if Instances == "00":
                pass

        PrivateIPAddresses = Players[5]
        if "," in PrivateIPAddresses:
            PrivateIPAddresses = PrivateIPAddresses.split(",")
            if len(PrivateIPAddresses) > 20:
                print("Might Have to Filter")
        if isinstance(PrivateIPAddresses, str):
            PrivateIPAddresses = [PrivateIPAddresses]
        for Instances in PrivateIPAddresses:
            if Instances == "00":
                pass
    cursor.close()
    conn.close()


@client.event
async def on_ready():
    print("NOTICE: Insight UDP Online")
    TCP.HaltSearch.HaltDatabase = False
    await zBlaze.main()
    client.tree.copy_global_to(guild=guild)
    await client.tree.sync(guild=guild)
    gateway_logger = logging.getLogger('discord.gateway')
    gateway_logger.setLevel(logging.ERROR)
    gateway_handler = logging.StreamHandler()
    gateway_logger.addHandler(gateway_handler)
    client_logger = logging.getLogger('discord.client')
    client_logger.setLevel(logging.ERROR)
    client_handler = logging.StreamHandler()
    client_logger.addHandler(client_handler)
    asyncio.create_task(BlazeAuto(True, 12, 0))


async def BlazePing(CounterWord):
    CounterDWord = swap32((32768 + CounterWord), 4)
    Counter = str(binascii.hexlify(int.to_bytes(CounterDWord, byteorder='big', length=4)))[2:-1]
    PingReq = bytes.fromhex("00 00 00 00 00 00 00 00 00 00 00 00 " + " ".join(Counter[i:i + 2] for i in range(0, len(Counter), 2)))
    try:
        zBlaze.Blaze.send(PingReq)
        await asyncio.sleep(0)
    except OSError:
        print("ERROR: Blaze Socket already closed, Restarting")
        return True
    LengthCount = 0
    Response = ""
    while True:
        try:
            Response = str(binascii.hexlify(zBlaze.Blaze.recv(1024)))[2:-1]
            await asyncio.sleep(0)
            if Response.startswith("0000000000000000"):
                break
            LengthCount += 1
            if LengthCount > 2000:
                print("ERROR: Blaze Socket Timeout, Restarting")
                return True
        except ssl.SSLWantReadError:
            if int(len(Response)) < 1:
                if LengthCount > 10:
                    print("ERROR: Blaze Socket Timeout, Restarting")
                    return True
                await asyncio.sleep(0.1)
                LengthCount += 1
                continue
        except OSError:
            print("ERROR: Blaze Socket already closed, Restarting")
            return True
    print("NOTICE: Ping Successful, Counter: " + Counter + ", Response = " + Response)
    return False


async def BlazeAuto(FirstScan, CounterWord, Code):
    memory_threshold = 2048 * 1024 * 1024
    try:
        while True:
            global ListPlayers
            conn = sqlite3.connect('PlayerDatabase.db')
            cursor = conn.cursor()
            cursor.execute("SELECT Username FROM players")
            try:
                ListPlayers = [row[0] for row in cursor.fetchall()]
            except MemoryError:
                print("ERROR: Memory Maxed out? Rebooting")
                await reboot()
            cursor.close()
            conn.close()
            PostReset = False
            if FirstScan:
                await asyncio.sleep(0)
                # if (Code % 15) == 0:       # Maybe in the future, filter DB from Old IPs
                #     await CleanDatabase()
                Code += 1
                AutoChannel = client.get_channel(1242348944764174396)
                GameListID = []
                PlayerTotal = 0
                SpartaRejectCount = 0
                BlazeRejectCount = 0
                CompleteList = []
                sparta_url_20_api = "https://" + zBlaze.SpartaIP + "/jsonrpc/pc/api?GameServer.searchServers"
                AreaTypes = ["EU", "NAm", "SAm", "Asia", "OC", "Afr", "AC"]
                SlotsTypes = ["tenPlus", "oneToFive", "sixToTen", "none"]
                for Area in AreaTypes:
                    for Slots in SlotsTypes:
                        await asyncio.sleep(0)
                        SpartaSearch = {"jsonrpc": "2.0", "method": "GameServer.searchServers", "params": {"filterJson": "{\"version\":7,\"slots\":{\"" + Slots + "\":\"on\"},\"regions\":{\"" + Area + "\":\"on\"}}", "game": "tunguska", "limit": 250, "protocolVersion": "3779779"}, "id": zBlaze.GetRandomID()}
                        try:
                            sparta_20_api = requests.post(sparta_url_20_api, headers=zBlaze.Sparta_02_Headers, json=SpartaSearch, verify=False)
                        except Exception:
                            print("ERROR: Sparta GW Timed-out, restarting")
                            await reboot()
                        try:
                            jsonSparta_20 = sparta_20_api.json()
                        except requests.exceptions.JSONDecodeError:
                            print("NOTICE: Likely Empty Option, disregard and continue")
                            continue
                        if jsonSparta_20["result"]['hasMoreResults']:
                            print("NOTICE: More non-included results For " + str(Area) + str(Slots))
                            embed = discord.Embed(color=16753920, description="``" + "NOTICE: Overflown Sparta GID Fetch, continuing" + str(Area) + str(Slots) + "``")
                            await AutoChannel.send(embed=embed)
                        for element in jsonSparta_20["result"]["gameservers"]:
                            await asyncio.sleep(0)
                            if element["slots"]["Soldier"]["current"] > 1:
                                GameListID.append(element["gameId"])
                            PlayerTotal += (element["slots"]["Soldier"]["current"])
                for Server in GameListID:
                    await restart_if_memory_exceeds(memory_threshold)
                    sys.argv.append('--myModuleParam')
                    sys.argv.append(Server)
                    zBlaze.parse_args()
                    await asyncio.sleep(0)
                    await zBlaze.main()
                    await asyncio.sleep(0)
                    sys.argv = [sys.argv[0]]
                    if zBlaze.UDPSession == -2:
                        print("ERROR: Ignoring server " + str(Server) + " since it is no longer online")
                        embed = discord.Embed(color=16776960, description="``" + "Ignoring server " + str(Server) + " since it is no longer online" + "``")
                        await AutoChannel.send(embed=embed)
                        continue
                    if zBlaze.UDPSession == -3:
                        SpartaRejectCount += 1
                        print("ERROR: Blocked Request from TCP Sparta, adding Server to the end of job and continuing..")
                        GameListID.append(Server)
                        if SpartaRejectCount == 3:
                            print("ERROR: 3x Blocked Request from TCP Sparta, flushing network and restarting scan")
                            embed = discord.Embed(color=16776960, description="``" + "3x Blocked Request from TCP Sparta, flushing network and restarting" + "``")
                            await AutoChannel.send(embed=embed)
                            PostReset = True
                            break
                        continue
                    else:
                        SpartaRejectCount = 0
                    if zBlaze.UDPSession == 1 or zBlaze.UDPSession == 2:
                        BlazeRejectCount += 1
                        print("ERROR: Blocked Request from TCP Blaze, adding Server to the end of job and continuing..")
                        GameListID.append(Server)
                        if BlazeRejectCount == 3:
                            print("ERROR: 3x Blocked Request from TCP Blaze, flushing network and restarting scan")
                            embed = discord.Embed(color=16776960, description="``" + "3x Blocked Request from TCP Blaze, flushing network and restarting" + "``")
                            await AutoChannel.send(embed=embed)
                            PostReset = True
                            break
                        continue
                    else:
                        BlazeRejectCount = 0
                    NameID = str(zBlaze.NameID).replace(",", "").replace("'", "").replace('"', "")
                    while NameID.startswith(" "):
                        NameID = NameID[1:]
                    CompleteList.append([zBlaze.NameOnlyScan, zBlaze.PIDOnlyScan, zBlaze.MACIOnlyScan, zBlaze.IPOnlyScan, str(Server + "," + NameID + "," + str(datetime.utcnow())[:-7])])
            await process_data(CompleteList, CounterWord, PostReset)
    except Exception:
        traceback.print_exc()


async def process_data(CompleteList, CounterWord, PostReset):
    global cursor
    global conn
    conn = sqlite3.connect('PlayerDatabase.db')
    cursor = conn.cursor()
    all_usernames = {Username for data in CompleteList for Username in data[0]}
    placeholders = ','.join('?' for _ in all_usernames)
    cursor.execute(f"SELECT * FROM players WHERE Username IN ({placeholders})", tuple(all_usernames))
    fetched_data = cursor.fetchall()
    fetched_dict = {row[1]: row for row in fetched_data}
    conn.execute('BEGIN')
    updates = []
    for Count, data in enumerate(CompleteList):
        for Username, PlayerID, MACAddress, PublicIPAddress, PrivateIPAddress, ServerInfo in zip(data[0], data[1], data[2], data[3][::2], data[3][1::2], [data[4]] * len(data[0])):
            ServerID, ServerName, ScanTime = ServerInfo.split(',')
            Fetched = fetched_dict.get(Username)
            if Fetched:
                SQPlayerID = Fetched[2].split(",") if "," in Fetched[2] else Fetched[2]
                SQMACAddress = Fetched[3].split(",") if "," in Fetched[3] else Fetched[3]
                SQPublicIPAddress = Fetched[4].split(",") if "," in Fetched[4] else Fetched[4]
                SQPrivateIPAddress = Fetched[5].split(",") if "," in Fetched[5] else Fetched[5]
                if Username == "GoToBelize":
                    pass
                if PlayerID != "00" and (isinstance(SQPlayerID, list) and str(PlayerID) not in SQPlayerID or not isinstance(SQPlayerID, list) and str(PlayerID) != str(SQPlayerID)):
                    updates.append(("UPDATE players SET PlayerID = PlayerID || ? WHERE Username = ?", ("," + str(PlayerID), Username)))
                if MACAddress != "00" and (isinstance(SQMACAddress, list) and MACAddress not in SQMACAddress or not isinstance(SQMACAddress, list) and MACAddress != SQMACAddress):
                    updates.append(("UPDATE players SET MACAddress = MACAddress || ? WHERE Username = ?", ("," + str(MACAddress), Username)))
                if PublicIPAddress != "00" and (isinstance(SQPublicIPAddress, list) and PublicIPAddress not in SQPublicIPAddress or not isinstance(SQPublicIPAddress, list) and PublicIPAddress != SQPublicIPAddress):
                    updates.append(("UPDATE players SET PublicIPAddress = PublicIPAddress || ? WHERE Username = ?", ("," + str(PublicIPAddress), Username)))
                if PrivateIPAddress != "00" and (isinstance(SQPrivateIPAddress, list) and PrivateIPAddress not in SQPrivateIPAddress or not isinstance(SQPrivateIPAddress, list) and PrivateIPAddress != SQPrivateIPAddress):
                    updates.append(("UPDATE players SET PrivateIPAddress = PrivateIPAddress || ? WHERE Username = ?", ("," + str(PrivateIPAddress), Username)))

                CurrentServer = Fetched[6].split(",") if Fetched[6] else []
                SQServerID01 = CurrentServer[0] if CurrentServer else None
                Count = 0
                for Occupied in Fetched[6:]:
                    if Occupied:
                        Count += 1
                if str(SQServerID01) == str(ServerID):
                    UpdateTime = f"{SQServerID01},{ServerName},{ScanTime}"
                    updates.append(("UPDATE players SET ServerInfo1 = ? WHERE Username = ?", (UpdateTime, Username)))
                else:
                    for i in range(Count, 0, -1):
                        if i == 10:
                            continue
                        try:
                            updates.append((f"UPDATE players SET ServerInfo{i + 1} = ServerInfo{i} WHERE Username = ?", (Username,)))
                        except Exception:
                            pass
                    ServerInfo = f"{ServerID},{ServerName},{ScanTime}"
                    updates.append(("UPDATE players SET ServerInfo1 = ? WHERE Username = ?", (ServerInfo, Username)))
            else:
                ServerInfo = f"{ServerID},{ServerName},{ScanTime}"
                updates.append(('INSERT INTO players (Username, PlayerID, MACAddress, PublicIPAddress, PrivateIPAddress, ServerInfo1) VALUES (?, ?, ?, ?, ?, ?)',
                                (Username, PlayerID, MACAddress, PublicIPAddress, PrivateIPAddress, ServerInfo)))
    AutoChannel = client.get_channel(1242348944764174396)
    embed = discord.Embed(color=65280, description="``" + " Successful heartbeat, Active Toll: " + str(len(updates)) + "``")
    await AutoChannel.send(embed=embed)
    print("NOTICE: Players To Fetch-> " + str(len(updates)))
    start_time = time.time()
    for i, (query, params) in enumerate(updates):
        try:
            cursor.execute(query, params)
        except sqlite3.ProgrammingError:
            conn = sqlite3.connect('PlayerDatabase.db')
            cursor = conn.cursor()
            cursor.execute(query, params)
        await asyncio.sleep(0)
        while TCP.HaltSearch.HaltDatabase:
            await asyncio.sleep(0)
        elapsed_time = time.time() - start_time
        if elapsed_time >= 20:
            Response = await BlazePing(CounterWord)
            if Response:
                PostReset = True
            else:
                CounterWord += 1
            start_time = time.time()
    conn.commit()
    cursor.close()
    conn.close()
    if PostReset:
        await VPNAPI.NewIdentity("0")
        await reboot()


async def whois_autocompletion(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    try:
        await interaction.response.defer(thinking=True)
    except discord.errors.NotFound:
        AutoChannel = client.get_channel(1242348944764174396)
        await AutoChannel.send("```ml\n VPS Lost Connection, Try Again, If Issue Continue, Attempt /Restart\n```")
        return
    global ListPlayers
    data = []
    for player_choice in ListPlayers:
        if current.lower() in player_choice.lower():
            data.append(app_commands.Choice(name=player_choice, value=player_choice))
    return data


@client.tree.command(description="Gathers all player's information saved within database")
@app_commands.autocomplete(player=whois_autocompletion)
async def whois(interaction: discord.Interaction, player: str):
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        AutoChannel = client.get_channel(1242348944764174396)
        await AutoChannel.send("```ml\n VPS Lost Connection, Try Again, If Issue Continue, Attempt /Restart\n```")
        return
    if interaction.channel_id != 1242348944764174396:
        await interaction.followup.send("```ml\nIncorrect Request, Insight-03's Commands Are Only Used For The Bot-Access-03 Channel\n```")
        return
    TCP.HaltSearch.HaltDatabase = True
    global cursor
    global conn
    try:
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
    except Exception:
        pass
    FetchPlayer = sqlite3.connect('PlayerDatabase.db')
    try:
        FetchCursor = FetchPlayer.cursor()
        FetchCursor.execute("SELECT * FROM players WHERE Username = ?", (player,))
        PlayerList = FetchCursor.fetchone()
        PlayerIDs = PlayerList[2]
    except Exception:
        await interaction.followup.send("```ml\nIncorrect Request, Select Username From Options\n```")
        return
    MACAddresses = PlayerList[3]
    PublicIPAddresses = PlayerList[4]
    PrivateIPAddresses = PlayerList[5]
    Servers = []
    for Server in PlayerList[6:15]:
        if Server:
            Server = Server.split(',')
            DateTime = Server[2]
            given_time = datetime.strptime(DateTime, '%Y-%m-%d %H:%M:%S')
            given_time = given_time.replace(tzinfo=timezone.utc)
            current_time = datetime.now(timezone.utc)
            time_difference = current_time - given_time
            time_components = []
            days = time_difference.days
            seconds = time_difference.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if days < 10:
                days = "0" + str(days)
            elif days > 99:
                days = "99"
            else:
                days = str(days)
            time_components.append(str(days))
            if hours < 10:
                hours = "0" + str(hours)
            else:
                hours = str(hours)
            time_components.append(str(hours))
            if minutes < 10:
                minutes = "0" + str(minutes)
            else:
                minutes = str(minutes)
            time_components.append(str(minutes))
            TimeDiff = ":".join(time_components) + " ->"
            if len(Server[1]) > 54:
                Name = Server[1][:54].ljust(55, " ")
            else:
                Name = Server[1].ljust(55, " ")
            Server = " " + str(TimeDiff.ljust(12, " ") + " " + Name)
            Servers.append(Server)
    if "," in MACAddresses:
        MACAddresses = MACAddresses.split(",")
    else:
        MACAddresses = [MACAddresses]
    if "," in PublicIPAddresses:
        PublicIPAddresses = PublicIPAddresses.split(",")
    else:
        PublicIPAddresses = [PublicIPAddresses]
    if "," in PrivateIPAddresses:
        PrivateIPAddresses = PrivateIPAddresses.split(",")
    else:
        PrivateIPAddresses = [PrivateIPAddresses]

    Personas = []
    FetchCursor.execute("SELECT * FROM players WHERE PlayerID = ?", (PlayerIDs,))
    Personas.append(FetchCursor.fetchall())

    for Public in PublicIPAddresses:
        if Public == "00":
            continue
        for Private in PrivateIPAddresses:
            if Private == "00":
                continue
            FetchCursor.execute("SELECT * FROM players WHERE PublicIPAddress = ? AND PrivateIPAddress = ?", (Public, Private,))
            Personas.append(FetchCursor.fetchall())

    for Private in PrivateIPAddresses:
        if Private == "00":
            continue
        for Public in PublicIPAddresses:
            if Public == "00":
                continue
            FetchCursor.execute("SELECT * FROM players WHERE PublicIPAddress = ? AND PrivateIPAddress = ?", (Public, Private,))
            Personas.append(FetchCursor.fetchall())

    for MAC in MACAddresses:
        if MAC == "00":
            continue
        FetchCursor.execute("SELECT * FROM players WHERE MACAddress = ?", (MAC,))
        Personas.append(FetchCursor.fetchall())

    GMTools = "https://api.gametools.network/manager/checkban/?name=" + str(PlayerList[1]) + "&platform=pc&skip_battlelog=false"
    try:
        FetchUsedNames = json.loads(requests.get(GMTools).content)["otherNames"]["usedNames"]
    except Exception:
        FetchUsedNames = ["Not Registered"]
    names_list = FetchUsedNames
    chunks = [names_list[i:i + 3] for i in range(0, len(names_list), 3)]
    PersonasExt = "\n Username ->  ".join(", ".join(chunk).ljust(55, " ") for chunk in chunks)
    if len(PublicIPAddresses) > 40:
        PublicIPAddresses = PublicIPAddresses[:40]
    EXIPLists = [[] for _ in range(6)]
    i = 0
    for PublicIPs in PublicIPAddresses:
        if PublicIPs == "00":
            EXIPLists[i].append("1.1.1.1")
        else:
            EXIPLists[i].append(str(PublicIPs))
        if len(EXIPLists[0]) == 16:
            i = 1
        if len(EXIPLists[1]) == 16:
            i = 2
        if len(EXIPLists[2]) == 16:
            i = 3
        if len(EXIPLists[3]) == 16:
            i = 4
        if len(EXIPLists[4]) == 16:
            i = 5
        if len(EXIPLists[5]) == 16:
            i = 6
    PlayerFullInfo = []
    for i in range(len(EXIPLists)):
        if EXIPLists[i]:
            JoinedIPScanList = ",".join(EXIPLists[i])
            IPScanURL = f"http://proxycheck.io/v2/{JoinedIPScanList}?key=01g741-596na2-2godv5-f23j96&vpn=1&asn=1&risk=1&port=1"
            ProxyCheckResult = requests.get(IPScanURL).content
            JSONDecode = json.loads(ProxyCheckResult)
            JSONDecode = list(JSONDecode.values())[1:]
        for IPINFO in JSONDecode:
            CNCode = IPINFO["isocode"]
            Proxy = IPINFO["proxy"]
            Type = IPINFO["type"]
            Country = IPINFO["isocode"]
            try:
                Region = IPINFO["region"]
            except KeyError:
                Region = "Unknown"
            try:
                City = IPINFO["city"]
            except Exception:
                City = "Unknown"
            try:
                Provider = IPINFO["provider"]
            except Exception:
                Provider = "Unknown"
            try:
                Organization = IPINFO["organisation"]
            except Exception:
                Organization = "Unknown"
            PlayerFullInfo.append([CNCode, Proxy, Type, Country, Region, City, Provider, Organization])
    Pers = []
    if len(Personas):
        for Persona in Personas:
            if Persona:
                if [x for x in Pers if str(Persona[0][1]) in str(x)]:
                    continue
                else:
                    Pers.append(str(" Username ->  " + str(Persona[0][1]).ljust(22) + " PlayerID-> " + str(Persona[0][2])).ljust(69, " "))
    else:
        Pers.append(str(" No Personas found in Database".ljust(69, " ")))
    RealLocations = []
    VPNLocations = []
    for Output in PlayerFullInfo:
        if Output[2] != "VPN":
            if len(Output[6]) > 14:
                CheckProv = Output[6][:14]
            else:
                CheckProv = Output[6]
            if [x for x in RealLocations if str(CheckProv) in str(x)]:
                continue
            else:
                Cat = str(" Category ->  " + Output[2])
                Loc = str(" Loc ->  " + Output[3] + ", " + Output[4] + ", " + Output[5])
                Prov = str(" Provider ->  " + Output[6])
                Org = str(" Org ->  " + Output[7])
                if len(Cat) > 28:
                    Cat = Cat[:28]
                if len(Prov) > 28:
                    Prov = Prov[:28]
                if len(Loc) > 39:
                    Loc = Loc[:39]
                if len(Org) > 39:
                    Org = Org[:39]
                Type = str(Cat).ljust(29) + str(Loc).ljust(40)
                ISP = str(Prov).ljust(29) + str(Org).ljust(40)
                RealLocations.append(Type)
                RealLocations.append(ISP)
                RealLocations.append("".rjust(68, "-") + " ")
        else:
            if len(Output[6]) > 14:
                CheckProv = Output[6][:14]
            else:
                CheckProv = Output[6]
            if [x for x in VPNLocations if str(CheckProv) in str(x)]:
                continue
            else:
                Cat = str(" Category ->  " + Output[2])
                Loc = str(" Loc ->  " + Output[3] + ", " + Output[4] + ", " + Output[5])
                Prov = str(" Provider ->  " + Output[6])
                Org = str(" Org ->  " + Output[7])
                if len(Cat) > 28:
                    Cat = Cat[:28]
                if len(Prov) > 28:
                    Prov = Prov[:28]
                if len(Loc) > 39:
                    Loc = Loc[:39]
                if len(Org) > 39:
                    Org = Org[:39]
                Type = str(Cat).ljust(29) + str(Loc).ljust(40)
                ISP = str(Prov).ljust(29) + str(Org).ljust(40)
                VPNLocations.append(Type)
                VPNLocations.append(ISP)
                VPNLocations.append("".rjust(68, "-") + " ")
    Locations = RealLocations + VPNLocations
    Personas = '\n'.join(Pers)
    PersonasExternal = " Username ->  " + PersonasExt
    NetworkLog = '\n'.join(Locations)
    ServersLog = '\n'.join(Servers)
    Content = " DD:HH:MM".ljust(14, " ") + "Last Played Servers".ljust(55, " ") + "\n" + ServersLog + "\n" + " ".ljust(69, " ") + "\n " + "Internal Database Check".rjust(36, "-").ljust(67, "-") + " \n" + Personas + "\n" + " ".ljust(69, " ") + "\n " + "External Database Check".rjust(36, "-").ljust(67, "-") + " \n" + PersonasExternal + "\n" + " ".ljust(69, " ") + "\n " + "Network Check".rjust(26, "-").ljust(67, "-") + " \n" + NetworkLog
    try:
        embed = discord.Embed(color=16753920, description="``" + Content + "``")
        await interaction.followup.send(embed=embed)
    except Exception:
        parts = []
        while len(Content) > 4050:
            split_index = Content.rfind('\n', 0, 4050)
            if split_index == -1:
                split_index = 4096
            parts.append(Content[:split_index])
            Content = Content[split_index:]
        parts.append(Content)
        for embeds in parts:
            embed = discord.Embed(color=65280, description="``" + embeds + "``")
            await interaction.followup.send(embed=embed)

    FetchCursor.close()
    FetchPlayer.close()
    TCP.HaltSearch.HaltDatabase = False
    return


@client.tree.command(description="Restart Insight-03")
async def restart(interaction: discord.Interaction):
    await interaction.response.defer()
    python_path = r'C:\Program Files\IDA 7.3\Python\Python311\python.exe'
    project_path = r'C:\Users\jonat\OneDrive\Bureau\Private Database\TCP\zDiscordBlaze.py'
    if interaction.channel_id != 1242348944764174396:
        await interaction.followup.send("```ml\nIncorrect Request, Insight-03's Commands Are Only Used For The secure-official-servers Channel\n```")
        return
    try:
        print("NOTICE: Closing Blaze Socket")
        zBlaze.Blaze.close()
        await interaction.followup.send("```fix\nRestarting Insight-03\n```")
        process = subprocess.Popen([python_path, project_path])
        process.wait()
    except Exception:
        traceback.print_exc()
        await interaction.followup.send("```ml\nIncorrect Request, Unknown Failure\n```")


async def reboot():
    python_path = r'C:\Program Files\IDA 7.3\Python\Python311\python.exe'
    project_path = r'C:\Users\jonat\OneDrive\Bureau\Private Database\TCP\zDiscordBlaze.py'
    print("NOTICE: Closing Blaze Socket")
    zBlaze.Blaze.close()
    print("NOTICE: Blaze Socket closed, attempting restart")
    process = subprocess.Popen([python_path, project_path])
    process.wait()

client.run(botToken)

