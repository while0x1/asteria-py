from pycardano import *
from staticVars import *
from dataclasses import dataclass
from cbor2  import CBORTag
from datetime import datetime
import time 
import sys

@dataclass()
class createShip(PlutusData):
    CONSTR_ID = 0
    x: int
    y: int
    shipName: bytes
    pilotName: bytes
    utcTime: int #UTCTime or slot + 300?

@dataclass()
class fuelPellet(PlutusData):
    CONSTR_ID = 0
    x: int
    y: int
    policy: bytes
 
@dataclass()
class authTokenDatum(PlutusData):
    shipCount: int
    policy: bytes
    CONSTR_ID = 0

@dataclass()
class shipFuelClaimRedeemer(PlutusData):
    CONSTR_ID = 1
    fuel: int
    

@dataclass()
class fuelClaimRedeemer(PlutusData):
    CONSTR_ID = 0
    fuelAmount: int
    

hdwallet = HDWallet.from_mnemonic(SEED)
hdwallet_stake = hdwallet.derive_from_path("m/1852'/1815'/0'/2/0")
stake_public_key = hdwallet_stake.public_key
stake_vk = PaymentVerificationKey.from_primitive(stake_public_key)
hdwallet_spend = hdwallet.derive_from_path("m/1852'/1815'/0'/0/0")
spend_public_key = hdwallet_spend.public_key
payment_vkey = PaymentVerificationKey.from_primitive(spend_public_key)
payment_skey = ExtendedSigningKey.from_hdwallet(hdwallet_spend)
stake_skey = StakeExtendedSigningKey.from_hdwallet(hdwallet)
stake_vkey = PaymentVerificationKey.from_primitive(stake_public_key)

userAddress = Address(payment_vkey.hash(),stake_vkey.hash(),network=Network.MAINNET)
#userAddress = Address(payment_vkey.hash(),network=Network.MAINNET)
print(f'User Address: {userAddress}')

OGMIOS_IP = '127.0.0.1'
shipName = B'SHIP4'
ship_name = shipName
pilot_name = b'PILOT4'
print(f'Defined Asteria Ship {shipName} piloted by {pilot_name}')

chain_context = OgmiosV6ChainContext(OGMIOS_IP,network=Network.MAINNET)
builder = TransactionBuilder(chain_context)
builder.add_input_address(userAddress)

print('Looking Asteria Reference inputs...')
ref_utxos_address = 'addr1w9mhn8s0qleh03mxwmlfyv4ekz790j5jc4sn9qturwsx6zcuxlz27'
ref_utxos = chain_context.utxos(ref_utxos_address)
print('Reference Inputs Located!')

auth_policy = 'db0d968cda2cc636b28c0f377e66691a065b8004e57be5129aeef822'
auth_token = MultiAsset.from_primitive({bytes.fromhex(auth_policy): {b'auth': 1 }})
pilot_policy = '0291ae7aebaf064b785542093c2b13169effb34462301e68d4b44f43'
fuel_policy = '3babcffc6102ec25ced40e1a24fba20371925c46f0299b2b9456360e'


print('Searching For your Ship in Asteria...')
ship_utxos = chain_context.utxos('addr1wypfrtn6awhsvjmc24pqj0ptzvtfalang33rq8ng6j6y7scnlkytx')



ship_utxo = None
##Find Your Ship UTXO

for n in ship_utxos:
    if n.output.amount.multi_asset:
        for a in n.output.amount.multi_asset:
            if a.payload.hex() == '0291ae7aebaf064b785542093c2b13169effb34462301e68d4b44f43':
                ma_list = list(n.output.amount.multi_asset.values())
                for items in ma_list:
                    find_asset = AssetName(shipName)
                    if find_asset in items:
                        print('Found Your Ship!')
                        ship_utxo = n
old_ship_datum = RawPlutusData.from_cbor(ship_utxo.output.datum.cbor)
old_ship_x = old_ship_datum.data.value[0]
old_ship_y = old_ship_datum.data.value[1]
old_ship_ma = ship_utxo.output.amount.multi_asset.to_primitive()
old_ship_fuel = old_ship_ma[bytes.fromhex(fuel_policy)][b'FUEL']


print(f'collecting fuel at {old_ship_x},{old_ship_y}')

x_coord = old_ship_x

y_coord = old_ship_y

foundFuel = False 
fuelMap = []
fuel_utxos = chain_context.utxos('addr1wya6hnluvypwcfww6s8p5f8m5gphryjugmcznxetj3trvrsc307jj')
for n in fuel_utxos:
    fdatum = RawPlutusData.from_cbor(n.output.datum.cbor)
    #print(fdatum)
    fuelX = fdatum.data.value[0]
    fuelY = fdatum.data.value[1]
    dist = abs(fuelX - x_coord) + abs(fuelY - y_coord)
    if fuelX == 16 and fuelY == 19:
        print(n)
    prox = False
    if dist < 6:
        prox = True
    fma = n.output.amount.multi_asset.to_primitive()
    fuelAmt = fma[bytes.fromhex(fuel_policy)][b'FUEL']
    fuelMap.append({'x':fuelX,'y':fuelY,'amount':fuelAmt,'proximity':prox, 'txHash':str(n.input.transaction_id) + "#" + str(n.input.index)})
    if fuelX == x_coord and fuelY == y_coord:
        print('found fuel pellet at location!')
        print(n)
        foundFuel =True 
        fuel_utxo = n
print('Fuel in Proximity to ship')
for n in fuelMap:
    if n['proximity']:
        print(n)
        
if not foundFuel:
    print('didnt find any refueling pellet at current location!')
    sys.exit()
    
#Need to input the utxo fuel asset you are consuming
#AddFuel and Ship Contract Utxos
#Max Fuel allowed 5 so only claim enough to refuel to 5
refuelingAmount = 5 - old_ship_fuel

shipRefuelRedeemer = Redeemer(shipFuelClaimRedeemer(refuelingAmount))
pelletRedeemer = Redeemer(fuelClaimRedeemer(refuelingAmount))

builder.add_script_input(fuel_utxo,script=ref_utxos[2],redeemer=pelletRedeemer)
builder.add_script_input(ship_utxo,script=ref_utxos[1],redeemer=shipRefuelRedeemer)

#keep Coordinates the same while refueling
UTC_now = int((time.time() + 350 ) * 1000)
#CreateNewShipDatum

#createShipDatum = createShip(x_coord,y_coord,ship_name,pilot_name,UTC_now)
#print('Created new ship datum')
#print(createShipDatum)
#SHIP_FUEL_MA = MultiAsset.from_primitive({bytes.fromhex(pilot_policy): {ship_name: 1},bytes.fromhex(fuel_policy): {b'FUEL': 5 }})
clone_ship_datum = RawPlutusData.from_cbor(ship_utxo.output.datum.cbor)
print(clone_ship_datum)
fuel_address = 'addr1wya6hnluvypwcfww6s8p5f8m5gphryjugmcznxetj3trvrsc307jj'
ship_holding_address = Address.from_primitive('addr1wypfrtn6awhsvjmc24pqj0ptzvtfalang33rq8ng6j6y7scnlkytx')
fuelDatum = fuelPellet(x_coord,y_coord,bytes.fromhex(pilot_policy))
#changeFuelAMount

#SHIP and FUEL assets going back to ship_holding contract after refuelling to full
SHIP_FUEL_MA = MultiAsset.from_primitive({bytes.fromhex(pilot_policy): {ship_name: 1},bytes.fromhex(fuel_policy): {b'FUEL': 5 }})
PILOT_MA = MultiAsset.from_primitive({bytes.fromhex(pilot_policy): {pilot_name: 1 }})

fuel_asset_amount_in = fuel_utxo.output.amount.multi_asset.to_primitive()[bytes.fromhex(fuel_policy)][b"FUEL"]
AUTH_FUEL_MA = MultiAsset.from_primitive({bytes.fromhex(fuel_policy): {b'FUEL': fuel_asset_amount_in - refuelingAmount},bytes.fromhex(auth_policy): {b'auth': 1 } })
fuel_address = 'addr1wya6hnluvypwcfww6s8p5f8m5gphryjugmcznxetj3trvrsc307jj'
ship_holding_address = Address.from_primitive('addr1wypfrtn6awhsvjmc24pqj0ptzvtfalang33rq8ng6j6y7scnlkytx')
builder.add_output(TransactionOutput(ship_holding_address,Value(1500000,SHIP_FUEL_MA), datum=clone_ship_datum))
builder.add_output(TransactionOutput(fuel_address,Value(fuel_utxo.output.amount.coin, AUTH_FUEL_MA), datum=fuelDatum))
builder.add_output(TransactionOutput(userAddress,Value(1500000,PILOT_MA)))

print(builder.inputs)
print(builder.outputs)
print(builder.redeemers())
print('Submit Refueling Tx? Y/N')
refuel_go = input()
if refuel_go == 'Y' or refuel_go == 'y':
    print('submitted tx')
    signed_tx = builder.build_and_sign([payment_skey], userAddress,auto_validity_start_offset=0,auto_ttl_offset=300)
    chain_context.submit_tx(signed_tx.to_cbor())
else:
    print('Aborted...')
