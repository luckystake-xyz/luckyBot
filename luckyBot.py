import subprocess
import json
import random
import requests
import collections
import time
import shlex

RPC_URL = 'https://api.mainnet-beta.solana.com'
VOTE_PUBKEY = 'Luck3DN3HhkV6oc7rPQ1hYGgU3b5AhdKW9o1ob6AyU9'

TICKETS_CAP = 1000
EPOCH_CAP = 12

POOLS = ["6iQKfEyhr3bZMotVkW6beNZz5CPAkiwvgV2CTje9pVSS", # Jito
         "4bZ6o3eUUNXhKuqjdCnCoPAoLgWiuLYixKaxoa8PpiKk", # Marinade
         "mpa4abUkjQoAvPzREkh5Mo75hZhPFQ2FSH6w7dWKuQ5",  # Solana Foundation
         "HbJTxftxnXgpePCshA8FubsRj9MW4kfPscfuUfn44fnt", # JPool
         "6WecYymEARvjG5ZyqkrVQ6YkhPfujNzWpSPwNKXHCbV2", # BlazeStake
         "noMa7dN4cHQLV4ZonXrC29HTKFpxrpFbDLK5Gub8W8t",  # MarinadeNative-legacy
         "stWirqFCf2Uts1JBL1Jsd3r6VBWhgnpdPxCTe1MFjrq",  # MarinadeNative
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

    def remove_stake(self, stakeAccount):
        self.activeStake -= stakeAccount['activeStake'] if stakeAccount.get('activeStake') else 0

    def createTickets(self, ticketCap):
        amountInSol = (self.activeStake + self.deactivatingStake + self.rentExemptReserve) / 10**9
        if amountInSol >= ticketCap:
            amountInSol = ticketCap
        if self.staker not in POOLS and amountInSol >= 1:
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

def setFile(filename, data1, data2=False, data3=False):
    result = {}
    result['result'] = data1
    if data2:
        result['tickets'] = data2
    if data3:
        result['boost'] = data3
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

def transferSol(destination, lamports, epoch):
    amount = lamports
    process = subprocess.Popen(shlex.split('ts-node /home/sol/transferBot/src/transferBot.ts --type transfer --destination %s --amount %s --epoch %s' % (destination, amount, epoch)),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout.decode('utf8')

def copyDB():
    process = subprocess.Popen(shlex.split('cp /home/sol/luckyBot/snapshots/stats.json /home/bot/db.json'),
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout

def gitPush(epoch):
    process = subprocess.Popen(shlex.split('/bin/bash /home/sol/luckyBot/gitPush.sh %s' % (epoch)),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout.decode('utf8')

def getBoost():
    try:
        headers = {'Content-Type': 'application/json'}
        req = requests.post("https://stake.solblaze.org/api/v1/cls_boost", headers=headers)
        bsolBoost = req.json()['boost']['conversion']
    except:
        bsolBoost = 1
    try:
        msol_tvl = requests.get("https://api.marinade.finance/tlv").json()
        price = requests.get("https://api.marinade.finance/msol/price_sol").json()
        msolBoost = (msol_tvl['total_sol'] * 0.2) / ( msol_tvl['msol_directed_stake_msol'] * price)
    except:
        msolBoost = 1
    try:
        v = requests.get("https://snapshots-api.marinade.finance/v1/votes/vemnde/latest").json()['records']
        ve_directed_stake_sum = sum(float(d.get('amount', 0)) for d in v if d['amount'] != None)
        ve_directed_LS = sum(float(d.get('amount', 0)) for d in v if d['amount'] != None and d['validatorVoteAccount'] == "Luck3DN3HhkV6oc7rPQ1hYGgU3b5AhdKW9o1ob6AyU9" )
        ratio = ( msol_tvl['total_sol'] * 0.2 / ve_directed_stake_sum )
        if ve_directed_LS * ratio <= msol_tvl['total_sol'] * 0.2 * 0.1:
            veMndeBoost = ratio
            veMndeMaxCap = False
        else:
            veMndeBoost = msol_tvl['total_sol'] * 0.2 * 0.1 / ve_directed_LS
            veMndeMaxCap = True
    except:
        veMndeBoost = 0
        veMndeMaxCap = False
    return {"msol": msolBoost, "bsol": bsolBoost, "native": 1, "veMnde": veMndeBoost, "veMndeMaxCap": veMndeMaxCap}

def getStakes(boost):
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

    # Add SolBlaze Stakers
    SolBlazePool = "6WecYymEARvjG5ZyqkrVQ6YkhPfujNzWpSPwNKXHCbV2"
    try:
        headers = {'Content-Type': 'application/json'}
        r = requests.post("https://stake.solblaze.org/api/v1/cls_applied_validator_stake?validator=Luck3DN3HhkV6oc7rPQ1hYGgU3b5AhdKW9o1ob6AyU9", headers=headers)
        b = r.json()
        for key, value in b['applied_stakes'].items():
            bStaker = {}
            bStaker['staker'] = key
            bStaker['activeStake'] = int(value * 10**9 * boost['bsol'])
            if bStaker['staker'] in stakers:
                stakers[bStaker['staker']].add_stake(bStaker)
                stakers[SolBlazePool].remove_stake(bStaker) # prevent double counting
            else:
                stakers[bStaker['staker']] = Staker(bStaker)
                stakers[SolBlazePool].remove_stake(bStaker) # prevent double counting
    except:
        print('SolBlaze fetch error')
        return 0

    # Add Marinade Stakers
    MarinadePool = "4bZ6o3eUUNXhKuqjdCnCoPAoLgWiuLYixKaxoa8PpiKk"
    try:
        price = requests.get("https://api.marinade.finance/msol/price_sol").json()
        r = requests.get("https://snapshots-api.marinade.finance/v1/votes/msol/latest")
        b = r.json()
        for record in b['records']:
            mStaker = {}
            if record['validatorVoteAccount'] == VOTE_PUBKEY and record['amount']:
                mStaker['staker'] = record['tokenOwner']
                mStaker['activeStake'] = int(float(record['amount']) * 10**9 * float(price) * boost['msol'])

                if mStaker['staker'] in stakers:
                    stakers[mStaker['staker']].add_stake(mStaker)
                    stakers[MarinadePool].remove_stake(mStaker) # prevent double counting
                else:
                    stakers[mStaker['staker']] = Staker(mStaker)
                    stakers[MarinadePool].remove_stake(mStaker) # prevent double counting
    except:
        print('Marinade fetch error')
        return 0

    # Add veMNDE Stakers
    try:
        r = requests.get("https://snapshots-api.marinade.finance/v1/votes/vemnde/latest").json()['records']
        for record in r:
            vmStaker = {}
            if record['validatorVoteAccount'] == VOTE_PUBKEY and record['amount']:
                vmStaker['staker'] = record['tokenOwner']
                vmStaker['activeStake'] = int(float(record['amount']) * boost['veMnde'] * 10**9)

                if vmStaker['staker'] in stakers:
                    stakers[vmStaker['staker']].add_stake(vmStaker)
                    stakers[MarinadePool].remove_stake(vmStaker) # prevent double counting
                else:
                    stakers[vmStaker['staker']] = Staker(vmStaker)
                    stakers[MarinadePool].remove_stake(vmStaker) # prevent double counting
    except:
        print('veMnde fetch error')
        return 0

    stakers = collections.OrderedDict(sorted(stakers.items()))
    return stakers

def getTickets(epoch):
    totalStake = 0
    totalTickets = 0
    stakersWithTickets = []
    stakerCurrentEpoch = {}

    stakers = getFile('%s.json' % int(epoch))
    if stakers:
        for value in stakers :
            value = Staker(value)
            stakerCurrentEpoch[value.staker] = int((value.activeStake + value.rentExemptReserve) / 10**9)

    for i in range(epoch - EPOCH_CAP + 1, epoch + 1):
        stakers = getFile('%s.json' % i)
        if stakers:
            for value in stakers :
                value = Staker(value)
                if value.staker in stakerCurrentEpoch:
                    tickets = value.createTickets(stakerCurrentEpoch[value.staker])
                    totalStake += int((value.activeStake + value.rentExemptReserve) / 10**9)
                    totalTickets += tickets
                    stakersWithTickets.append(value.__dict__)
    return stakersWithTickets

def getLucky(epoch, stakersWithTickets, ticketsStats):
    totalTickets = sum(list(ticketsStats.values()))
    slotReward = getSlotReward(epoch)
    slotHash = getSlot(slotReward['slot'])['blockhash']
    random.seed(slotHash)
    lucky = random.randrange(0, totalTickets)
    while lucky == 0:
        lucky = random.randrange(0, totalTickets)
    for value in stakersWithTickets :
        if value['tickets'][0] <= lucky and value['tickets'][1] >= lucky:
            luckyStaker = {"epoch":epoch, "slotReward":slotReward['slot'], "totalReward":slotReward['rewardLamports'], "luckyTicket":lucky, "totalTickets":totalTickets, "lamport":int(slotReward['rewardLamports']/2),"staker":value['staker'],"luckyTx":"pending", "communityTx":"deprecated"}
    return luckyStaker

def getStats(epochInfo, stakers):
    epoch = epochInfo['epoch']
    absoluteSlot = epochInfo['absoluteSlot']
    slotIndex = epochInfo['slotIndex']
    slotsInEpoch = epochInfo['slotsInEpoch']
    firstSlot = absoluteSlot - slotIndex
    lastSlot = firstSlot + slotsInEpoch - 1
    uniqueStakers = 0
    sumActivatingStake = 0
    sumActiveStake = 0
    sumDeactivatingStake = 0
    for key, values in stakers.items():
        uniqueStakers += 1 if values.activeStake + values.deactivatingStake > 0 else 0
        sumActivatingStake += values.activatingStake if values.activatingStake else 0
        sumActiveStake += values.activeStake if values.activeStake else 0
        sumDeactivatingStake += values.deactivatingStake if values.deactivatingStake else 0
    return {"epoch":epoch,"firstSlot":firstSlot,"lastSlot":lastSlot,"apy":0,"uniqueStakers":uniqueStakers,"activatingStake":sumActivatingStake, "activeStake": sumActiveStake, "deactivatingStake":sumDeactivatingStake, "lucky":{}}

def getTicketsStats(stakersWithTickets):
    tickets={}
    for item in stakersWithTickets:
        if item['tickets'][0]:
            if item['staker'] in tickets:
                tickets[item['staker']] += item['tickets'][1] - item['tickets'][0] + 1
            else:
                tickets[item['staker']] = item['tickets'][1] - item['tickets'][0] + 1
    sorted_tickets = sorted(tickets.items(), key=lambda x:x[1], reverse=True)
    sorted_dict = dict(sorted_tickets)
    return sorted_dict

if __name__ == "__main__":
    while True:
        try:
            epochInfo = getEpoch()
            epoch = epochInfo['epoch']
            epochProgress = epochInfo['slotIndex'] / epochInfo['slotsInEpoch']
            epoch_stats = getFile("stats.json")

            # New Epoch ?
            if epoch == int(epoch_stats[-1]['epoch']) + 1 and epochProgress > 0.002:
                print(epoch)

                # getStakes for new Epoch
                boost = getBoost()
                stakers = getStakes(boost)

                if not stakers:
                    print('No stakers, break')
                    break

                # Update stats
                Newstats = getStats(epochInfo, stakers)

                # Get tickets
                stakersWithTickets = getTickets(epoch_stats[-1]['epoch'])
                # Get tickets Stats
                ticketsStats = getTicketsStats(stakersWithTickets)

                # Draw lucky Staker
                lucky = getLucky(epoch_stats[-1]['epoch'], stakersWithTickets, ticketsStats)
                epoch_stats[-1]['lucky'] = lucky

                # APY
                if len(epoch_stats[-2]['lucky'])>2:
                    firstBlock = epoch_stats[-2]['lucky']['slotReward']
                    slotReward = getSlotReward(epoch_stats[-1]['epoch'])
                    lastBlock  = getSlot(slotReward['slot'])['parentSlot']
                    firstTime = getSlot(firstBlock)['blockTime']
                    lastTime = getSlot(lastBlock)['blockTime']
                    slotTimeInSec = lastTime - firstTime
                    YearInSec = 31536000
                    rewardsEpoch = epoch_stats[-1]['lucky']['totalReward'] * 100 / 4
                    N = slotTimeInSec / YearInSec
                    RATE = rewardsEpoch / epoch_stats[-1]['activeStake']
                    apy = RATE / N
                    apy = round(apy, 4)
                else:
                    apy = 0

                epoch_stats[-1]['apy'] = apy
                epoch_stats.append(Newstats)
                setFile("stats.json", epoch_stats, ticketsStats, boost)

                ## Create new snapshot file
                list = []
                for key, values in stakers.items():
                    list.append(values.__dict__)
                setFile('%s.json' % epoch, list)

                #### TRANSFERT TO WINNER
                epoch_stats = getFile("stats.json") # Update stats file
                print(epoch_stats[-2]['lucky'])
                txid_1 = transferSol(epoch_stats[-2]['lucky']['staker'], epoch_stats[-2]['lucky']['lamport'], epoch_stats[-2]['lucky']['epoch'])

                # Log result
                epoch_stats[-2]['lucky']['luckyTx'] = txid_1
                setFile("stats.json", epoch_stats, ticketsStats, boost)

                # Copy to JSON-server
                copyDB()
                gitPush(epoch - 1)

            elif  epoch == int(epoch_stats[-1]['epoch']) and epochProgress < 0.998:
                #EPOCH EXIST
                boost = getBoost()
                stakers = getStakes(boost)

                if not stakers:
                    break

                """LOG ALL STAKERS"""
                list = []
                for key, values in stakers.items():
                    list.append(values.__dict__)

                # Get Tickets
                stakersWithTickets = getTickets(epoch_stats[-1]['epoch'])
                # Get tickets Stats
                ticketsStats = getTicketsStats(stakersWithTickets)

                # Update stats file
                setFile('%s.json' % epoch, list)
                Newstats = getStats(epochInfo, stakers)
                epoch_stats[-1] = Newstats
                setFile("stats.json", epoch_stats, ticketsStats, boost)

                copyDB()
            time.sleep(60*5)
        except Exception as e:
            print(e)
            time.sleep(30)
            break
