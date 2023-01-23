import subprocess
import json
import random
import requests
import collections
import time
import shlex

RPC_URL = 'https://api.mainnet-beta.solana.com'
VOTE_PUBKEY = 'Luck3DN3HhkV6oc7rPQ1hYGgU3b5AhdKW9o1ob6AyU9'

TICKETS_CAP = 5000
EPOCH_CAP = 12

POOLS = ["6iQKfEyhr3bZMotVkW6beNZz5CPAkiwvgV2CTje9pVSS", # Jito
         "4bZ6o3eUUNXhKuqjdCnCoPAoLgWiuLYixKaxoa8PpiKk", # Marinade
         "mpa4abUkjQoAvPzREkh5Mo75hZhPFQ2FSH6w7dWKuQ5",  # Solana Foundation
        ]


class Staker(object):
    ticket = 1
    def __init__(self, stakeAccount):
        self.staker = stakeAccount['staker']
        self.activatingStake = stakeAccount['activatingStake'] if stakeAccount.get('activatingStake') else 0
        self.activeStake = stakeAccount['activeStake'] if stakeAccount.get('activeStake') else 0
        self.deactivatingStake = stakeAccount['deactivatingStake'] if stakeAccount.get('deactivatingStake') else 0
        self.rentExemptReserve = stakeAccount['rentExemptReserve'] if stakeAccount.get('rentExemptReserve') else 0

    def add_stake(self, stakeAccount):
        self.activatingStake += stakeAccount['activatingStake'] if stakeAccount.get('activatingStake') else 0
        self.activeStake += stakeAccount['activeStake'] if stakeAccount.get('activeStake') else 0
        self.deactivatingStake += stakeAccount['deactivatingStake'] if stakeAccount.get('deactivatingStake') else 0
        self.rentExemptReserve += stakeAccount['rentExemptReserve'] if stakeAccount.get('rentExemptReserve') else 0

    def createTickets(self):
        if self.staker not in POOLS:
            amountInSol = (self.activeStake + self.rentExemptReserve) / 10**9
            if amountInSol < TICKETS_CAP:
                tickets = amountInSol
            else:
                tickets = TICKETS_CAP + 0.5*(amountInSol-TICKETS_CAP)
            tickets = int(tickets)
            self.tickets = [Staker.ticket, Staker.ticket + tickets - 1]
            Staker.ticket = Staker.ticket + tickets
        else:
            tickets = 0
            self.tickets = [0, 0]
        return tickets

def getFile (filename):
    url = '/home/sol/luckyBot/snapshots/' + filename
    try:
        with open(url, "r") as epochfile:
            result = json.load(epochfile)
            epochfile.close()
            return result['result']
    except:
        return False

def setFile(filename, data):
    result = {}
    result['result'] = data
    url = '/home/sol/luckyBot/snapshots/' + filename
    try:
        with open(url, "w") as epochfile:
            json.dump(result, epochfile)
            epochfile.close()
        return 1
    except:
        return 0

def getSlot(slot):
    payload = {'jsonrpc': '2.0','id':1,'method':'getBlock','params':[slot, {"encoding": "json","transactionDetails":"none","rewards":False}]}
    headers = {'Content-Type': 'application/json'}
    try:
        r = requests.post(RPC_URL, data=json.dumps(payload), headers=headers)
        j = r.json()
        return j['result']
    except:
        return 0

def getSlotReward(epoch):
    payload = {"jsonrpc":"2.0","id":1, "method":"getInflationReward", "params": [[VOTE_PUBKEY], {"epoch": epoch}]}
    headers = {'Content-Type': 'application/json'}
    try:
        r = requests.post(RPC_URL, data=json.dumps(payload), headers=headers)
        j = r.json()
        slot = j['result'][0]['effectiveSlot']
        reward = j['result'][0]['amount']
        return {"slot":slot, "rewardLamports":reward}
    except:
        return 0

def getEpoch():
    payload = {"jsonrpc":"2.0","id":1, "method":"getEpochInfo"}
    headers = {'Content-Type': 'application/json'}
    try:
        r = requests.post(RPC_URL, data=json.dumps(payload), headers=headers)
        j = r.json()
        return j['result']
    except:
        return 0

def copyDB():
    process = subprocess.Popen(shlex.split('cp /home/sol/luckyBot/snapshots/stats.json /home/bot/db.json'),
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    print(stdout)
    return stdout

def getStakes():
    stakers = {}
    process = subprocess.Popen(shlex.split('solana stakes --url %s --output json %s' % (RPC_URL,VOTE_PUBKEY)),
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    jsonStakes = stdout.decode('utf8').replace("'", '"')
    dataStakes = json.loads(jsonStakes)

    for stake in dataStakes :
        if stake['staker'] in stakers:
            stakers[stake['staker']].add_stake(stake)
        else:
            stakers[stake['staker']] = Staker(stake)

    stakers = collections.OrderedDict(sorted(stakers.items()))
    return stakers

def getLucky(epoch):
    totalStake = 0
    totalTickets = 0
    stakersWithTickets = []

    for i in range(epoch - EPOCH_CAP - 1, epoch + 1):
        stakers = getFile('%s.json' % i)
        stakers = false
        if stakers:
            for value in stakers :
                value = Staker(value)
                tickets = value.createTickets()
                totalStake += int((value.activeStake + value.rentExemptReserve) / 10**9)
                totalTickets += tickets
                stakersWithTickets.append(value.__dict__)

    slotReward = getSlotReward(epoch)
    print(slotReward, epoch)
    slotHash = getSlot(slotReward['slot'])['blockhash']
    random.seed(slotHash)
    lucky = random.randrange(0, totalTickets)

    for value in stakersWithTickets :
        if value['tickets'][0] <= lucky and value['tickets'][1] >= lucky:
            luckyStaker = {"epoch":epoch, "slotReward":slotReward['slot'], "totalReward":slotReward['rewardLamports'], "luckyTicket":lucky, "totalTickets":totalTickets, "lamport":int(slotReward['rewardLamports']/3),"staker":value['staker'],"luckyTx":"pending"}
    return luckyStaker

def getStats(epochInfo, stakers):
    epoch = epochInfo['epoch']
    absoluteSlot = epochInfo['absoluteSlot']
    slotIndex = epochInfo['slotIndex']
    slotsInEpoch = epochInfo['slotsInEpoch']
    firstSlot = absoluteSlot - slotIndex
    lastSlot = firstSlot + slotsInEpoch - 1
    uniqueStakers = len(stakers)
    sumActivatingStake = 0
    sumActiveStake = 0
    sumDeactivatingStake = 0
    for key, values in stakers.items():
        sumActivatingStake += values.activatingStake if values.activatingStake else 0
        sumActiveStake += values.activeStake if values.activeStake else 0
        sumDeactivatingStake += values.deactivatingStake if values.deactivatingStake else 0
    return {"epoch":epoch,"firstSlot":firstSlot,"lastSlot":lastSlot,"apy":0,"uniqueStakers":uniqueStakers,"activatingStake":sumActivatingStake, "activeStake": sumActiveStake, "deactivatingStake":sumDeactivatingStake, "lucky":{}}

if __name__ == "__main__":
    while True:
        try:
            epochInfo = getEpoch()
            epoch = epochInfo['epoch']
            epoch_stats = getFile("stats.json")

            # New Epoch ?
            if epoch == int(epoch_stats[-1]['epoch']) + 1:
                print('New Epoch', epoch)

                # getStakes for new Epoch
                stakers = getStakes()

                # Update stats file
                Newstats = getStats(epochInfo, stakers)

                # Draw lucky Staker
                lucky = getLucky(epoch_stats[-1]['epoch'])

                epoch_stats[-1]['lucky'] = lucky

                # APY
                if len(epoch_stats[-2]['lucky'])>2:
                    firstBlock = epoch_stats[-2]['lucky']['slotReward']
                    lastBlock = epoch_stats[-1]['lastSlot']
                    print(firstBlock, lastBlock)
                    firstTime = getSlot(firstBlock)['blockTime']
                    lastTime = getSlot(lastBlock)['blockTime']
                    slotTimeInSec = lastTime - firstTime
                    YearInSec = 31536000
                    rewardsEpoch = epoch_stats[-1]['lucky']['totalReward'] * 100 / 6
                    N = slotTimeInSec / YearInSec
                    RATE = rewardsEpoch / epoch_stats[-1]['activeStake']
                    apy = RATE / N
                    apy = round(apy, 4)
                else:
                    apy = 0
                epoch_stats[-1]['apy'] = apy
                epoch_stats.append(Newstats)
                setFile("stats.json", epoch_stats)

                ## Create new snapshot file
                list = []
                for key, values in stakers.items():
                    list.append(values.__dict__)
                setFile('%s.json' % epoch, list)

                #### TRANSFERT TO WINNER
                # ToDo

                # Log result
                #epoch_stats[-2]['lucky']['luckyTx'] = txId
                #setFile("stats.json", epoch_stats)

                # Copy to JSON-server
                copyDB()
                print('TRANSERT SOL',lucky['staker'], lucky['lamport']/10**9)


            else:
                #EPOCH EXIST
                stakers = getStakes()

                """LOG ALL STAKERS"""
                list = []
                for key, values in stakers.items():
                    list.append(values.__dict__)

                # Update stats file
                setFile('%s.json' % epoch, list)
                Newstats = getStats(epochInfo, stakers)
                epoch_stats[-1] = Newstats
                setFile("stats.json", epoch_stats)


                copyDB()
            time.sleep(60*5)
        except:
            # Stats file exist ? Else create stats file
            if not epoch_stats:
                stakers = getStakes()
                stats = getStats(epochInfo, stakers)
                setFile("stats.json", [stats])
                epoch_stats = getFile("stats.json")
            print('error')
            time.sleep(15)
