import argparse
import sys
import glob
import time
from os import path, system
import subprocess
import toml
from collections import OrderedDict
import time
import tempfile

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

    print('Starting services')
    system('docker-compose pull dapptools indexer-db contact-watcher-db statediff-migrations indexer-graphql eth-watcher-ts')
    system('docker-compose up -d dapptools indexer-db contact-watcher-db statediff-migrations indexer-graphql')
    print('Waiting for eht-watcher-ts service to be up and running')
    system('docker-compose up -d eth-watcher-ts')
    system('while [[ "$(curl -s -o /dev/null -w ''%{http_code}'' localhost:3001/v1/healthz)" != "200" ]]; do echo "waiting..." && sleep 5; done')

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
        print(
            f'Copying contract "{contract}" to dapptool container ...')
        exec_geth('rm -rf /tmp/src && mkdir -p /tmp/src')
        cp_geth(path.join(dir_path, contract + '.sol'), contract + '.sol')

        print(f'Building contracts {contract}...')
        exec_geth('cd /tmp && dapp build --extract')

        print(f'Deploying contract {contract}...')

        ts = int(time.time()) + 20
        print(f'Current timestamp is {ts}')

        out, _ = exec_geth(
            f'cd /tmp && ETH_FROM={coinbase} ETH_RPC_ACCOUNTS=1 SETH_VERBOSE=1 ETH_GAS=0xffffff dapp create {config_contract[contract]["name"]}')
        contract_address = out.rstrip()
        print(f'Contract {contract} address is {contract_address}')

        # get contract ABI
        out, _ = exec_geth(
            f'cat /tmp/out/{config_contract[contract]["name"]}.abi')
        abi = out.rstrip()
        # print(f'ABI is {abi}')

        print(f'writing config for {contract}...')
        # events
        # TODO get from config
        system("docker-compose exec contact-watcher-db sh -c \"psql -U vdbm -d vulcanize_public -c \\\"INSERT INTO "
               "contract.events(name) VALUES ('MessageChanged') ON CONFLICT DO NOTHING;\\\"\"")
        # copy sql file
        fp = open("a.sql", "w")
        fp.write(str("INSERT INTO contract.contracts (name, address, abi, events, starting_block) VALUES ('" +
                         contract + "', '" + contract_address + "', '" +
                         abi + "', '{1}', 1);"))
        fp.close()
        system(f'cat {fp.name}')
        system(
            f'docker cp "{fp.name}" $(docker-compose ps -q contact-watcher-db):/tmp/contract.sql')
        system(
            "docker-compose exec contact-watcher-db sh -c \"psql -U vdbm -d vulcanize_public < /tmp/contract.sql\"")

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
