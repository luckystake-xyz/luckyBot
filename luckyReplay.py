import subprocess
import json
import random
import requests
import collections
import time
import shlex
import sys

RPC_URL = 'https://api.mainnet-beta.solana.com'
VOTE_PUBKEY = 'Luck3DN3HhkV6oc7rPQ1hYGgU3b5AhdKW9o1ob6AyU9'
COMMUNITY_WALLET = ''

TICKETS_CAP = 5000
EPOCH_CAP = 12

POOLS = ["6iQKfEyhr3bZMotVkW6beNZz5CPAkiwvgV2CTje9pVSS", # Jito
         "4bZ6o3eUUNXhKuqjdCnCoPAoLgWiuLYixKaxoa8PpiKk", # Marinade
         "mpa4abUkjQoAvPzREkh5Mo75hZhPFQ2FSH6w7dWKuQ5",  # Solana Foundation
         "HbJTxftxnXgpePCshA8FubsRj9MW4kfPscfuUfn44fnt", # JPool
         "6WecYymEARvjG5ZyqkrVQ6YkhPfujNzWpSPwNKXHCbV2", # BlazeStake
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

    def createTickets(self):
        amountInSol = (self.activeStake + self.deactivatingStake + self.rentExemptReserve) / 10**9
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

def getLucky(epoch):
    totalStake = 0
    totalTickets = 0
    stakersWithTickets = []

    for i in range(epoch - EPOCH_CAP - 1, epoch + 1):
        stakers = getFile('%s.json' % i)
        if stakers:
            for value in stakers :
                value = Staker(value)
                tickets = value.createTickets()
                totalStake += int((value.activeStake + value.rentExemptReserve) / 10**9)
                totalTickets += tickets
                stakersWithTickets.append(value.__dict__)
    slotReward = getSlotReward(epoch)
    print (json.dumps(stakersWithTickets,indent=4)) # REPLAY
    slotHash = getSlot(slotReward['slot'])['blockhash']
    random.seed(slotHash)
    lucky = random.randrange(0, totalTickets)

    for value in stakersWithTickets :
        if value['tickets'][0] <= lucky and value['tickets'][1] >= lucky:
            luckyStaker = {"epoch":epoch, "slotReward":slotReward['slot'], "totalReward":slotReward['rewardLamports'], "luckyTicket":lucky, "totalTickets":totalTickets, "lamport":int(slotReward['rewardLamports']/3),"staker":value['staker'],"luckyTx":"pending", "communityTx":"pending"}
    print(json.dumps(luckyStaker,indent=4)) # REPLAY
    return luckyStaker

if __name__ == "__main__":
    # python3 luckyReplay.py <EPOCH>
    lucky = getLucky(int(sys.argv[1])) # REPLAY
