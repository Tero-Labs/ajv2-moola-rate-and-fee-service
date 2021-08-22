from celo_sdk.kit import Kit
import json
import datetime
from pycoingecko import CoinGeckoAPI
from fastapi import FastAPI,Depends, Query # Query = for length checking

from fastapi.middleware.cors import CORSMiddleware

from enum import Enum
from typing import Optional
import requests

app = FastAPI( title="Moola Rate and Fee Service API",
    description="To Serve MobileApps & Dashboards",
    version="0.1.0",)

# --------- CORS -----------
origins = [
     "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#-------- End of CORS ---------

class ActivityPermittedList(str, Enum):
	deposit = "deposit"
	withdraw = "withdraw"
	borrow = "borrow"
	repay = "repay"
	liquidate = "liquidate"

coin_dict = {
"cUSD": "cusd",
"Celo": "celo",
"cEUR": "ceuro"
}

class CurrencyPermittedList(str, Enum):
	cUSD = "cUSD"
	Celo = "Celo"
	cEUR = "cEUR"

address_regex = '/[a-fA-F0-9]{40}$/'

Default_Currency = 'Celo'

with open("./abis/LendingPool.json") as f:
    Lending_Pool = json.load(f)

with open("./abis/IPriceOracleGetter.json") as f:
    IPrice_Oracle_Getter = json.load(f)  

with open("./abis/feeProvider.json") as f:
    Fee_Oracle_Getter = json.load(f)  

with open("./abis/LendingPoolAddressesProvider.json") as f:
    Lending_Pool_Addresses_Provider = json.load(f)  

with open("./abis/LendingPoolDataProvider.json") as f:
    Lending_Pool_Data_Provider = json.load(f)  

with open("./abis/LendingPoolCore.json") as f:
    Lending_Pool_Core = json.load(f)  

alphajores_kit = Kit('https://alfajores-forno.celo-testnet.org') 
alfajores_lendingPool = alphajores_kit.w3.eth.contract(address="0x0886f74eEEc443fBb6907fB5528B57C28E813129", abi= Lending_Pool)

def get_latest_block(celo_testnet_web3): 
    celo_testnet_web3.middleware_onion.clear()
    blocksLatest = celo_testnet_web3.eth.getBlock("latest")
    return int(blocksLatest["number"], 16)  
'''
  Start of Fee service
'''
cg = CoinGeckoAPI()

helper_w3 = Kit('https://alfajores-forno.celo-testnet.org').w3
ether = 1000000000000000000

kit = Kit('https://alfajores-forno.celo-testnet.org')
gas_contract = kit.base_wrapper.create_and_get_contract_by_name('GasPriceMinimum')

web3 = kit.w3
eth = web3.eth


celo_testnet_address_provider = eth.contract(address='0x6EAE47ccEFF3c3Ac94971704ccd25C7820121483', abi=Lending_Pool_Addresses_Provider) 
fee_provider_address = celo_testnet_address_provider.functions.getFeeProvider().call()
lending_core_address = celo_testnet_address_provider.functions.getLendingPoolCore().call()
lending_pool_address = celo_testnet_address_provider.functions.getLendingPool().call()
lendingPoolDataProvider_address = celo_testnet_address_provider.functions.getLendingPoolDataProvider().call()


lendingPool = eth.contract(address= lending_pool_address, abi= Lending_Pool) 
lendingPoolDataProvider = eth.contract(address= lendingPoolDataProvider_address, abi= Lending_Pool_Data_Provider) 
# print(lendingPool.functions.getReserves().call())

# print(lending_pool_address)
gas_contract = kit.base_wrapper.create_and_get_contract_by_name('GasPriceMinimum')

coin_reserve_address = {
        "celo": "0xF194afDf50B03e69Bd7D057c1Aa9e10c9954E4C9",
        "cusd": "0x874069Fa1Eb16D44d622F2e0Ca25eeA172369bC1",
        "ceuro":"0x10c892A6EC43a53E45D0B916B4b7D383B1b78C0F"
}

coins_reserve_address = {
        "celo": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "cusd": "0x874069Fa1Eb16D44d622F2e0Ca25eeA172369bC1",
        "ceuro":"0x10c892A6EC43a53E45D0B916B4b7D383B1b78C0F"
}

def get_gas_price(coin_name):    
    return gas_contract.get_gas_price_minimum(coin_reserve_address[coin_name.lower()])


def estimate_gas_amount(activity, amount, coin_name, user_address):
    amount = web3.toWei(amount, 'wei')
    # print("Coin reserve address: " + coin_reserve_address[coin_name.lower()])
    # print("Amount: " + str(amount))
    # print(" User Address: " + web3.toChecksumAddress(user_address))
    if activity == 'deposit':
        if coin_name == 'celo':
            call_obj = {'from': web3.toChecksumAddress(user_address), 'value': amount }
        elif coin_name == 'ceuro':
            call_obj = {'from': web3.toChecksumAddress(user_address) } 
        else:  
            call_obj = {'from': web3.toChecksumAddress(user_address) }

        return lendingPool.functions.deposit(coins_reserve_address[coin_name.lower()], amount, 0).estimateGas(call_obj)
    elif activity == 'borrow':
        return lendingPool.functions.borrow(coins_reserve_address[coin_name.lower()], amount, 2, 0).estimateGas({
            'from': web3.toChecksumAddress(user_address), 
        })
    elif activity == 'repay':
        if coin_name == 'ceuro':
            return lendingPool.functions.repay(coins_reserve_address[coin_name.lower()], amount, web3.toChecksumAddress('0xa3464A9410616034D3A736446e1de3eC9176ABA0')).estimateGas({
                'from': web3.toChecksumAddress(user_address), 
                'value': amount
            })
        else:
            return lendingPool.functions.repay(coins_reserve_address[coin_name.lower()], amount, web3.toChecksumAddress('0x863A2e0C0A02C654f231e421C47B64d1c86eFd56')).estimateGas({
                'from': web3.toChecksumAddress(user_address), 
                'value': amount
            })
    elif activity == 'withdraw':
        return lendingPool.functions.redeemUnderlying(coins_reserve_address[coin_name.lower()], web3.toChecksumAddress('0x313bc86D3D6e86ba164B2B451cB0D9CfA7943e5c'), amount, 0).estimateGas({
            'from': web3.toChecksumAddress(user_address), 
            })

    
def wei_to_celo(price_in_wei):
    return ((price_in_wei/ether)*cg.get_price(ids='ethereum', vs_currencies='usd')['ethereum']['usd'])/cg.get_price(ids='celo', vs_currencies='usd')['celo']['usd']


### get the fees in celo
def get_fee(activity, amount, coin_name, user_address):
    try:
        estimated_gas_amount = estimate_gas_amount(activity, amount, coin_name, user_address)
    except Exception as e:
        print(e)
        print("From historical.")
        estimated_gas_amount = historical_gas_amount[activity][coin_name]
    price_in_celo = estimated_gas_amount * (wei_to_celo(get_gas_price(coin_name)))
    
    # print("Estinated gas amount:")
    # print(estimated_gas_amount)
    # print(estimate_gas_amount(activity, amount, coin_name, user_address)/amount)
    if coin_name == "cusd":
        cusd_exchange_rate = get_price_in_celo('cusd', coins_reserve_address['cusd'])
        return price_in_celo /cusd_exchange_rate 
    elif coin_name == "ceuro":
        ceur_exchange_rate = get_price_in_celo("ceuro", coins_reserve_address["ceuro"])
        return price_in_celo / ceur_exchange_rate
    return price_in_celo

historical_gas_amount = {
            'deposit': {
                "celo": 178885,
                "cusd": 213517,
                "ceuro": 176837
            },
            'borrow': {
                "celo": 373567,
                "cusd": 382804,
                "ceuro": 413753
            },
            'repay': {
                "celo": 162417,
                "cusd": 204310,
                "ceuro": 199664
            },
            'withdraw': {
                "celo": 129545,
                "cusd": 158204,
                "ceuro": 158678
            },
        }   

activity_address = {
            'deposit': {
                "Celo": "0xa0bda5d71291f391a71bf2d695b4ea620ac7b0e6",
                "cUSD": "0x8767abbe8a753a8d608d3440947b85ebcee7c4cc",
                "cEUR": "0xF194afDf50B03e69Bd7D057c1Aa9e10c9954E4C9"
            },
            'borrow': {
                "Celo": "0xa0bda5d71291f391a71bf2d695b4ea620ac7b0e6",
                "cUSD": "0x8daE998C630d3D959aF0621a8d2ae52f13D0Ca13",
                "cEUR": "0x8daE998C630d3D959aF0621a8d2ae52f13D0Ca13"
            },
            'repay': {
                "Celo": "0xa0bda5d71291f391a71bf2d695b4ea620ac7b0e6",
                "cUSD": "0x8daE998C630d3D959aF0621a8d2ae52f13D0Ca13",
                "cEUR": "0x8a045c8dcb7977425aa5a13887477d0dd4c2c28e"
            },
            'withdraw': {
                "Celo": "0x7037F7296B2fc7908de7b57a89efaa8319f0C500",
                "cUSD": "0x64dEFa3544c695db8c535D289d843a189aa26b98",
                "cEUR": "0xa8d0E6799FF3Fd19c6459bf02689aE09c4d78Ba7"
            },
        }   


   

ether = 1000000000000000000
def getInEther(num):
    return num/ether

def get_debt_assets(currency):
    return [x for x in ['Celo', 'cUSD', 'cEUR'] if x != currency]



def get_collateral_currencies(address):
    collateral_currencies, debt_currencies = [], []
    try:
        user_reserve_data = lendingPool.functions.getUserReserveData(coins_reserve_address['celo'], web3.toChecksumAddress("0x" + address)).call()
        print(user_reserve_data)
        if user_reserve_data[9] == True:
            collateral_currencies.append("Celo")
        if user_reserve_data[1] > 0:
            debt_currencies.append("Celo")
    except Exception as e:
        print(e)
    try:
        user_reserve_data = lendingPool.functions.getUserReserveData(coins_reserve_address['cusd'], web3.toChecksumAddress("0x" + address)).call()
        print(user_reserve_data)
        if user_reserve_data[9] == True:
            collateral_currencies.append("cUSD")
        if user_reserve_data[1] > 0:
            debt_currencies.append("cUSD")
    except Exception as e:
        print(e) 
    try:
        user_reserve_data = lendingPool.functions.getUserReserveData(coins_reserve_address['ceuro'], web3.toChecksumAddress("0x" + address)).call()
        print(user_reserve_data)
        if user_reserve_data[9] == True:
            collateral_currencies.append("cEUR")
        if user_reserve_data[1] > 0:
            debt_currencies.append("cEUR")   
    except Exception as e:
        print(e)
    return ",".join(collateral_currencies), debt_currencies
    


'''
  End of Fee service
'''

'''
  Start of Rate service
'''


price_oracle = eth.contract(address='0x88A4a87eF224D8b1F463708D0CD62b17De593DAd', abi= IPrice_Oracle_Getter)
fee_oracle = eth.contract(address=fee_provider_address, abi= Fee_Oracle_Getter)


security_fee_oracle = eth.contract(address=lending_core_address, abi= Lending_Pool_Core)
# print(lending_core_address)
def get_origination_fee_borrow(borrower, amount):
    return fee_oracle.functions.calculateLoanOriginationFee(web3.toChecksumAddress(borrower), int(amount)).call()/ether
print(get_origination_fee_borrow("0xe2d85bf29d96d5fe4f2f312873fc60fd91ea2266", int(ether*0.4883687378009934)))

def get_origination_fee_repay(coin_name, borrower):
    # print(coins_reserve_address[coin_name])
    return security_fee_oracle.functions.getUserOriginationFee(coins_reserve_address[coin_name], web3.toChecksumAddress(borrower)).call()/ether
# print(get_origination_fee_repay('ceuro', "0xdedfe7c341ffcb43c26bdb17d6a59c2317907f36"))




# print("Security fee: ")
# print(get_origination_fee_repay('cusd', "0xf5b1bc6c9c180b64f5711567b1d6a51a350f8422"))
# print(get_origination_fee_repay('celo', "0x796c27ab58c626075de11519dd4a49573f64967f"))



# @app.get("/get/getBorrowerFee")
# async def get_getBorrowedFee(address, amount: int = None, currency_borrowed: Optional[CurrencyPermittedList] = Default_Currency):
#     executionDateTime = datetime.datetime.now(datetime.timezone.utc).timestamp()
#     orignation_fee = get_origination_fee("0x"+address, amount)
#     security_fee = get_security_fee(coin_dict[currency_borrowed], "0x"+address)
#     return {'status':'OK',
# 			'dateTime':executionDateTime,
# 			'coinName': currency_borrowed,
# 			'OriginationFee': orignation_fee,
#             'SecurityFee': security_fee
# 			}


def get_exchange_rate_in_usd(coin_name, coin_address):
    price_in_celo = get_price_in_celo(coin_name, coin_address)
    return price_in_celo*cg.get_price(ids='celo', vs_currencies='usd')['celo']['usd']

def get_price_in_celo(coin_name, coin_address):
    return price_oracle.functions.getAssetPrice(coin_address).call()/ether
#test getRateInUsd
# print(get_exchange_rate_in_usd("celo", coins_reserve_address["celo"]))

# /get/getRateInUsd
#http://127.0.0.1:8000/get/getRateInUsd?coin_name=celo
@app.get("/get/getRateInUsd")
async def get_getFee(coin_name: CurrencyPermittedList):
    
	executionDateTime = datetime.datetime.now(datetime.timezone.utc).timestamp()


	exchange_rate_in_usd = get_exchange_rate_in_usd(coin_name, coins_reserve_address[coin_dict[coin_name]] )

	return {'status':'OK',
			'dateTime':executionDateTime,
			'coinName': coin_name,
			'RateInUsd': exchange_rate_in_usd,
			}

'''
  End of Rate service
'''

@app.get("/get/getLiquidationPrice")
async def get_liquidation_price(userPublicKey: str):
    executionDateTime = datetime.datetime.now(datetime.timezone.utc).timestamp()
    # altCurrency, altCollateralCurrency = collateralCurrency, currency
    currencies, debt_assets = get_collateral_currencies(userPublicKey)
    response = []
    
    if currencies != "" and debt_assets != []:
        currencylist = currencies.split(',')
        coins_reserve_address = {
            "celo": '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE',
            "cusd": '0x874069Fa1Eb16D44d622F2e0Ca25eeA172369bC1' , 
            "ceuro": '0x10c892A6EC43a53E45D0B916B4b7D383B1b78C0F'  
        }  
        # celo_price_cusd, celo_price_ceur = get_price_in_celo("cusd", coins_reserve_address["cusd"]), get_price_in_celo("ceuro", coins_reserve_address["ceuro"])
        celo_usd, cusd_usd, ceuro_usd = get_exchange_rate_in_usd("celo", coins_reserve_address["celo"]), get_exchange_rate_in_usd("cusd", coins_reserve_address["cusd"]),get_exchange_rate_in_usd("ceuro", coins_reserve_address["ceuro"])
        cusd_in_celo, ceuro_in_celo = get_price_in_celo("cusd", coins_reserve_address["cusd"]), get_price_in_celo("ceuro", coins_reserve_address["ceuro"])

        currency_prices = {
            'Celo': {
                "Celo": 1,
                "cUSD": 1/cusd_in_celo,
                "cEUR": 1/ceuro_in_celo
            },
            'cUSD': {
                "Celo": cusd_in_celo,
                "cUSD": 1,
                "cEUR": cusd_usd/ceuro_usd
            },
            'cEUR': {
                "cUSD": ceuro_usd/cusd_usd,
                "Celo": ceuro_in_celo,
                "cEUR": 1
            },
        }     
        liquidation_prices = {
            'Celo': {
                "cUSD": 0,
                "cEUR": 0
            },
            'cUSD': {
                "Celo": 0,
                "cEUR": 0
            },
            'cEUR': {
                "cUSD": 0,
                "Celo": 0
            },
        }
        block_number = get_latest_block(helper_w3)
        
        # print(block_number)
        try:
            print("User key "+ userPublicKey)
            user_account_data = lendingPool.functions.getUserAccountData(web3.toChecksumAddress("0x" + userPublicKey)).call(block_identifier=block_number)
            
       
        except Exception as e:
            print(e)
            user_account_data = lendingPoolDataProvider.functions.calculateUserGlobalData(web3.toChecksumAddress("0x" + userPublicKey)).call(block_identifier=block_number)
     
        finally:
            total_in_eth = getInEther(user_account_data[1])
            total_in_debt = getInEther(user_account_data[2])
            total_in_fees = getInEther(user_account_data[3])
            # total_in_eth = getInEther(user_account_data[1])
            # total_in_debt = getInEther(user_account_data[2])
            liquidation_price = 0.0
            if total_in_eth != 0.0 and total_in_debt != 0.0:
                health_factor = (total_in_eth*0.8)/(total_in_debt+total_in_fees)
                Liquidation_price_celo_in_celo = 1/(health_factor)
                liquidation_prices["Celo"]["Celo"] = Liquidation_price_celo_in_celo 
                liquidation_prices["cUSD"]["cUSD"] = Liquidation_price_celo_in_celo 
                liquidation_prices["cEUR"]["cEUR"] = Liquidation_price_celo_in_celo 
                liquidation_prices["Celo"]["cUSD"] = Liquidation_price_celo_in_celo * currency_prices["Celo"]["cUSD"]
                liquidation_prices["Celo"]["cEUR"] = Liquidation_price_celo_in_celo * currency_prices["Celo"]["cEUR"]
                liquidation_prices["cUSD"]["Celo"] = Liquidation_price_celo_in_celo * currency_prices["cUSD"]["Celo"]
                liquidation_prices["cUSD"]["cEUR"] = Liquidation_price_celo_in_celo * currency_prices["cUSD"]["cEUR"]
                liquidation_prices["cEUR"]["Celo"] = Liquidation_price_celo_in_celo * currency_prices["cEUR"]["Celo"]
                liquidation_prices["cEUR"]["cUSD"] = Liquidation_price_celo_in_celo * currency_prices["cEUR"]["cUSD"]
            response = {"collateral": currencies, "collateralAssets": [] }  
            # print(len(currencylist))
            for currency in currencylist:
                # print(currency)
                for debt_asset in debt_assets:
                    # print(currency, debt_asset)
                    # print(currency_prices)
                    collateralAsset = {
                        "currency": currency,
                        "liquidationPrice": liquidation_prices[currency][debt_asset],
                        "currentPrice": currency_prices[currency][debt_asset],
                        "priceCurrency": debt_asset
                    }
                    response["collateralAssets"].append(collateralAsset)
    return {'status':'OK',
        		'dateTime':executionDateTime,
        		'coinName': currencies,
        		'data': response
        		}

def get_response_with_loan_origination_fee(activity, address, currency, amount, final_response):
    loan_origination_fee = 0
    # print(currency)
    try:
        if activity == "borrow":
            if currency == "Celo":
                print(amount)
                print(ether)
                loan_origination_fee = get_origination_fee_borrow("0x"+address, int(ether*amount))
            elif currency == "cUSD":
                cusd_exchange_rate =  get_price_in_celo('cusd', coins_reserve_address['cusd'])
                loan_origination_fee = get_origination_fee_borrow("0x"+address, int(ether*amount*cusd_exchange_rate))/cusd_exchange_rate
                
            elif currency == "cEUR":
                ceuro_exchange_rate = get_price_in_celo('ceuro', coins_reserve_address['ceuro']) 
                loan_origination_fee = get_origination_fee_borrow("0x"+address, int(ether*amount*ceuro_exchange_rate))/ceuro_exchange_rate
            
       
        else:
            # print("Calculate repay: ")
            # print(coin_dict)
            # print("currency: "+ coin_dict[currency])
            # print("Address" + "0x"+address)
            loan_origination_fee = get_origination_fee_repay(coin_dict[currency], "0x"+address)
            print("loan_origination_fee: "+ str(loan_origination_fee))
    except Exception as e:
        print("Error: ")
        print(e)
        loan_origination_fee = 0
    finally:
        
            
        final_response["loanOriginationFee"]  = loan_origination_fee
        # print("loan_origination_fee: " + str(loan_origination_fee))
        return final_response        

# currency, activityType = "Celo", "borrow"
# print(coin_dict[currency], activity_address[activityType][currency])

# /get/getFee
#http://127.0.0.1:8000/get/getFee?userPublicKey=011ce5bd73a744b2b5d12265be37250defb5b590&activityType=borrow&amount=40.0
@app.get("/get/getFee")
async def get_getFee(userPublicKey: str, activityType: ActivityPermittedList = None, amount:float = None,currency: Optional[CurrencyPermittedList] = Default_Currency):

	executionDateTime = datetime.datetime.now(datetime.timezone.utc).timestamp()
	print("currency and activityType: ")
	# print(coin_dict)
	# print(activity_address)
    
	print("Currency: "+ str(currency))
	print("Activity: "+ str(activityType))
	print(coin_dict[currency], activity_address[activityType][currency])
    
	TotalFee = get_fee(activityType, amount, coin_dict[currency], activity_address[activityType][currency])

	
	final_response = {
                    'status':'OK',
                    'dateTime':executionDateTime,
                    'currency': currency,
                    'activity': activityType,
                    'amount': float(amount),
                    'securityFee': TotalFee
    }
	if activityType == "borrow" or activityType == "repay":
	    return get_response_with_loan_origination_fee(activityType, userPublicKey, currency, amount, final_response)
	return final_response
	



# print(get_liquidation_pricee("8a045c8dcb7977425aa5a13887477d0dd4c2c28e"))
### test get_fee
# print(get_fee("borrow", 150, 'ceuro', "0x84cd08f5de891f82f6bd2938b06ed84f6abab5e7"))
# print(get_gas_price('cusd'))0xa3464A9410616034D3A736446e1de3eC9176ABA0
# print(get_gas_price('celo'))0x863A2e0C0A02C654f231e421C47B64d1c86eFd56
# print(get_gas_price('ceuro'))

# print("deposit celo:")
# print(get_fee("deposit", 100, 'celo', "0xa0bda5d71291f391a71bf2d695b4ea620ac7b0e6"))
# print("deposit cusd:")
# print(get_fee("deposit", 1500, 'cusd', "0x8767abbe8a753a8d608d3440947b85ebcee7c4cc"))
# print("deposit ceur:")
# print(get_fee("deposit", 1, 'ceuro', "0x5083043abfceadd736a97ce32a71ac7a1386e449"))
# print("\nBorrow celo:")
# # print(get_fee("a0bda5d71291f391a71bf2d695b4ea620ac7b0e6", "borrow", 1500.5, 'Celo'))
# print(get_fee("borrow", 1500, 'celo', "0x8daE998C630d3D959aF0621a8d2ae52f13D0Ca13"))
# print("Borrow cusd:")
# print(get_fee("borrow", 1500, 'cusd', "0x8daE998C630d3D959aF0621a8d2ae52f13D0Ca13"))
# print("Borrow ceur:")
# print(get_fee("borrow", 1500, 'ceuro', "0x8daE998C630d3D959aF0621a8d2ae52f13D0Ca13"))
# print("\nRepay celo:")
# print(get_fee("repay", 1500, 'celo', "0xa0bda5d71291f391a71bf2d695b4ea620ac7b0e6"))
# print("Repay cusd:")
# print(get_fee("repay", 1500, 'cusd', "0x8daE998C630d3D959aF0621a8d2ae52f13D0Ca13"))
# print("Repay ceur:")
# print(get_fee("repay", 1500, 'ceuro', "0x8a045c8dcb7977425aa5a13887477d0dd4c2c28e"))
# print("\nWithdraw celo:")
# print(get_fee("withdraw", 1500, 'celo', "0x7037F7296B2fc7908de7b57a89efaa8319f0C500"))
# print("Withdraw cusd:")
# print(get_fee("withdraw", 1500, 'cusd', "0x64dEFa3544c695db8c535D289d843a189aa26b98"))
# print("Withdraw ceur:")
# print(get_fee("withdraw", 1500, 'ceuro', "0xa8d0E6799FF3Fd19c6459bf02689aE09c4d78Ba7"))

# print(get_fee("deposit", 1500, 'cusd', "0xa0bda5d71291f391a71bf2d695b4ea620ac7b0e6"))

# print(get_fee("deposit", 1500, 'ceuro', "0x8daE998C630d3D959aF0621a8d2ae52f13D0Ca13"))

# print(get_fee("repay", 1500, 'ceuro', "0xa0bda5d71291f391a71bf2d695b4ea620ac7b0e6"))




# celo_usd, cusd_usd, ceuro_usd = get_exchange_rate_in_usd("celo", coins_reserve_address["celo"]), get_exchange_rate_in_usd("cusd", coins_reserve_address["cusd"]),get_exchange_rate_in_usd("ceuro", coins_reserve_address["ceuro"])
# currency_prices = {
#             'Celo': {
#                 "Celo": 1,
#                 "cUSD": celo_usd/cusd_usd,
#                 "cEUR": celo_usd/ceuro_usd
#             },
#             'cUSD': {
#                 "Celo": cusd_usd/celo_usd,
#                 "cUSD": 1,
#                 "cEUR": cusd_usd/ceuro_usd
#             },
#             'cEUR': {
#                 "cUSD": ceuro_usd/cusd_usd,
#                 "Celo": ceuro_usd/celo_usd,
#                 "cEUR": 1
#             },
#         }

# print(get_price_in_celo("celo", coin_reserve_address["cusd"]))   
# print(get_price_in_celo("cusd", coins_reserve_address["cusd"]))   
# print(get_price_in_celo("ceuro", coins_reserve_address["ceuro"]))   
# print(currency_prices['Celo']['cUSD'])
# print(currency_prices['cEUR']['cUSD'])
# print(currency_prices['Celo']['cEUR'])
# print(currency_prices['cUSD']['cEUR'])