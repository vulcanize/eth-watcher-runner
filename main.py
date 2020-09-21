import argparse
import sys
import glob
import time
from os import path, system
import subprocess
import toml
from collections import OrderedDict

parser = argparse.ArgumentParser()
parser.add_argument("path", help="path to directory with smart contracts",
                    type=str)
args = parser.parse_args()

# ./script.py --contract1 = a.sol --parameter1=ABC --contract2=b.sol --parameter=ZZZ

gethContainerId = ''


def main():
    dir_path: str = args.path
    if not path.exists(dir_path):
        sys.exit(f'Directory {dir_path} does not exist')

    config = toml.load('config.toml')
    config_contract = config['contract']
    contracts = config_contract['contracts']
    if len(contracts) == 0:
        sys.exit(f'Could not find contract list in config')

    contract_watcher_config = toml.load('environments/contract-watcher.example.toml')

    print('Starting geth node')
    system('docker-compose up -d dapptools indexer-db contact-watcher-db eth-indexer eth-server eth-header-sync')
    print('Waiting 100 sec')
    time.sleep(100)

    process = subprocess.Popen(['docker-compose', 'ps', '-q', 'dapptools'],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True)
    stdout, stderr = process.communicate()
    if stderr != '':
        sys.exit(stderr)

    global gethContainerId
    gethContainerId = stdout.rstrip()
    # sys.exit(0)

    contractFiles = glob.glob(dir_path + '/*.sol')
    if len(contractFiles) == 0:
        sys.exit(f'Could not find *.sol files in {dir_path} directory')

    # copy all smart contract files to dapptool docker container
    for contractFile in contractFiles:
        _, contract_file_name = path.split(contractFile)
        print(f'Copying contract "{contract_file_name}" to dapptool container ...')
        exec_geth('rm -rf /tmp/src && mkdir -p /tmp/src')
        cp_geth(contractFile, contract_file_name.rstrip())

    out, _ = exec_geth('seth rpc eth_coinbase')
    coinbase = out.rstrip()
    print(f'Coinbase is {coinbase}')
    print(f'Building contracts...')
    exec_geth('cd /tmp && dapp build --extract')

    addresses = []
    for contract in contracts:
        _, contract_file_name = path.split(contract)

        print(f'Deploying contract {contract}...')
        out, _ = exec_geth(f'cd /tmp && ETH_FROM={coinbase} ETH_RPC_ACCOUNTS=1 SETH_VERBOSE=1 ETH_GAS=0xffffff dapp create ' + config_contract[contract]['name'])
        contract_address = out.rstrip()
        print(f'Contract {contract} address is {contract_address}')

        # update docker-compose for postgraphile (add schema)
        system(f"sed -i 's/SCHEMA=public/SCHEMA=public,header_{contract_address.lower()}/' docker-compose.yml")

        # get contract ABI
        out, _ = exec_geth(f'cat /tmp/out/{config_contract[contract]["name"]}.abi')
        abi = out.rstrip()
        # print(f'ABI is {abi}')
        addresses.append({'address': contract_address, 'abi': abi})

    print('writing contract-watcher config')
    addrs = []
    for i in addresses:
        addrs.append(i['address'])
        contract_watcher_config['contract'][i['address']] = OrderedDict()
        contract_watcher_config['contract'][i['address']]['abi'] = i['abi']
        contract_watcher_config['contract'][i['address']]['startingBlock'] = 0

    contract_watcher_config['contract']['addresses'] = addrs

    with open('environments/example.toml', 'w') as f:
        toml.dump(contract_watcher_config, f)

    # run contract watcher
    system('docker-compose up -d eth-contract-watcher')
    # time.sleep(10)
    # system('docker-compose up -d contract-watcher-graphql')


def exec_geth(command: str):
    command_list = ['sh', '-c', command]
    # print(command_list)
    final_cmd = ['docker', 'exec', gethContainerId] + command_list
    # print(final_cmd)
    process = subprocess.Popen(final_cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True)
    stdout, stderr = process.communicate()
    # print(stdout, stderr)

    if process.returncode != 0:
        sys.exit('Error' + stderr)

    return stdout, stderr


def cp_geth(local_file: str, docker_file: str):
    final_cmd = ['docker', 'cp', local_file, gethContainerId + ':/tmp/src/' + docker_file]
    # print(final_cmd)
    process = subprocess.Popen(final_cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True)
    stdout, stderr = process.communicate()
    # print(stdout, stderr)
    if stderr != '':
        sys.exit(stderr)

    return stdout


if __name__ == '__main__':
    main()
