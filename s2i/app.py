#!/usr/bin/env python3

# import requests
import pystache
import os
from getpass import getpass
import json
import sys
import base64
import boto3
import time


def get_rh_id(default):
    rh_id = input('RH subscription-manager ID [' +
                  default + ']:')
    rh_id = rh_id or default
    return rh_id


def get_reg_pool(default):
    reg_pool = input('RH subscription pool id (RHEL) [' +
                     default + ']:')
    reg_pool = reg_pool or default
    return reg_pool


def get_ec2_key(default):
    ec2_key = input('ec2 key name [' +
                    default + ']:')
    ec2_key = ec2_key or default
    return ec2_key


def get_aws_profile_name(default):
    aws_profile_name = input('AWS profile name [' +
                             default + ']:')
    aws_profile_name = aws_profile_name or default
    return aws_profile_name


def get_aws_subnet_id(default):
    aws_subnet_id = input('AWS Subnet ID \n' +
                          "(Most of the time this will 'default')" +
                          '[' + default + ']:')

    aws_subnet_id = aws_subnet_id or default
    return aws_subnet_id


def get_aws_security_group_id(default):
    aws_security_group_id = input('AWS profile name [' +
                                  default + ']:')
    aws_security_group_id = aws_security_group_id or default
    return aws_security_group_id


def get_git_ssh_file(default):
    print('SSH key file for source code repo access.  This is an optional')
    print('key to be used by a user config script ')
    git_ssh_file = input('enter /dev/null if no key is needed. [' +
                         default + ']:')
    git_ssh_file = git_ssh_file or default
    return git_ssh_file


def get_user_script_file(default):
    user_script_file = input('Optional script to run inside openshift ' +
                             'container.' +
                             '\nUse this to configure apps, policies, etc. [' +
                             default + ']:')
    user_script_file = user_script_file or default
    return user_script_file


def get_rh_password(default):
    rh_password = getpass('Subscription Manager password ' +
                          '[cached password]:')
    rh_password = rh_password or default
    return rh_password


def get_ose_public_master(default):
    ose_public_master = input('Openshift public master hostname' +
                              '[use xip.io]:')

    ose_public_master = ose_public_master or default
    return ose_public_master


def get_ose_admin_password(default):
    ose_admin_password = getpass('Openshift admin password ' +
                                 '[cached password]:')
    ose_admin_password = ose_admin_password or default
    return ose_admin_password


# Retrieve an EC2 instance tag.
def get_ec2_instance_tags(default):
    print(default)
    # If there are any tags in the cache,
    # print them and then ask if the user wants to use them
    if any(default):
        print("\nCached Tags:\n")
        for k, v in default.items():
            print(k, '=', v)

        print("\n")
        user_input = "something"    # get the loop started
        while not (user_input == 'yes' or
                   user_input == 'no' or
                   user_input == ""):

            user_input = input('Use these tags [yes]:')
            print(user_input.lower())
            if user_input.lower() == 'yes' or user_input.lower() == '':
                # use cached tags
                return default

    # get new tags
    print('Enter blank "key" to quit.')
    tags_dict = {}
    key = 'something'    # set key to something to start the loop
    while not key == "":
        key = input('key: ')
        if key == "":
            return tags_dict
        value = input('value: ')
        if value == "":
            print("Value cannot be null.")
        else:
            tags_dict[key] = value


def create_ec2_instance(ec2, ec2_instance_tags,
                        ec2_key, script, aws_security_group_id, aws_subnet_id):
    if aws_subnet_id is None:
        #
        instances = ec2.create_instances(
            ImageId='ami-775e4f16',
            MinCount=1,
            MaxCount=1,
            KeyName=ec2_key,
            UserData=script,
            InstanceType='t2.medium',
            BlockDeviceMappings=[
                {
                    'DeviceName': '/dev/sdb',
                    'Ebs': {
                        'VolumeSize': 50,
                        'DeleteOnTermination': True,
                      }
                },
                {
                    'DeviceName': '/dev/sdc',
                    'Ebs': {
                        'VolumeSize': 20,
                        'DeleteOnTermination': True,
                    }
                }
            ],
        )
    else:
            #
            instances = ec2.create_instances(
                SubnetId=aws_subnet_id,
                ImageId='ami-775e4f16',
                MinCount=1,
                MaxCount=1,
                KeyName=ec2_key,
                SecurityGroupIds=[
                    aws_security_group_id,
                    ],
                UserData=script,
                InstanceType='t2.medium',
                BlockDeviceMappings=[
                    {
                        'DeviceName': '/dev/sdb',
                        'Ebs': {
                            'VolumeSize': 50,
                            'DeleteOnTermination': True,
                          }
                    },
                    {
                        'DeviceName': '/dev/sdc',
                        'Ebs': {
                            'VolumeSize': 20,
                            'DeleteOnTermination': True,
                        }
                    }
                ],
            )

    print("Created EC2 instance ID " + instances[0].instance_id)

    time.sleep(5)

    for k, v in ec2_instance_tags.items():
        response = ec2.create_tags(
                                   Resources=[instances[0].instance_id],
                                   Tags=[{
                                          'Key': k, 'Value': v
                                        }])

        print(response)


def main():
    # deploys all in one OSE on ec2
    # you can see what was passed as user-data to an ec2 instance by doing
    # curl -s http://169.254.169.254/latest/user-data
    # on the instance.

    # first check for ec2 credentials
    f = open(os.environ['HOME'] + '/.aws/credentials', 'r')
    f.read()
    f.close()

    f = open(os.environ['HOME'] + "/.aws/config", 'r')
    f.read()
    f.close()

    try:
        f = open(os.environ['HOME'] + '/.osdd/deploy-ose.json', 'r')
        cached_deploy_json = f.read()
        f.close
        cached_deploy_dict = json.loads(cached_deploy_json)
        print("Cache file loaded.")

    except:
        print("No cache file found.")
        cached_deploy_dict = {'rh_id': '',
                              'rh_password': '',
                              'reg_pool': '',
                              'ec2_key': '',
                              'git_ssh_file': '',
                              'ec2_instance_tags': {},
                              'ose_admin_password': '',
                              'user_script_file': "",
                              'aws_profile_name': "",
                              'aws_subnet_id': ""}

    rh_id = ''
    while not rh_id:
        rh_id = get_rh_id(cached_deploy_dict['rh_id'])

    rh_password = ''
    while not rh_password:
        rh_password = \
          get_rh_password(cached_deploy_dict['rh_password'])

    reg_pool = ''
    while not reg_pool:
        reg_pool = \
          get_reg_pool(cached_deploy_dict['reg_pool'])

    aws_profile_name = ''
    while not aws_profile_name:
        aws_profile_name = get_aws_profile_name(
            cached_deploy_dict['aws_profile_name'])

    ec2_instance_tags = {}
    while not any(ec2_instance_tags):
        ec2_instance_tags = \
          get_ec2_instance_tags(cached_deploy_dict['ec2_instance_tags'])

    ec2_key = ''
    while not ec2_key:
        ec2_key = get_ec2_key(cached_deploy_dict['ec2_key'])

    aws_subnet_id = ''
    while not aws_subnet_id:
        aws_subnet_id = get_aws_subnet_id(cached_deploy_dict['aws_subnet_id'])

    if aws_subnet_id.lower() != "default":
        aws_security_group_id = ''
        while not aws_security_group_id:
            aws_profile_name = aws_security_group_id(
                cached_deploy_dict['aws_security_group_id'])

    ose_public_master = ''
    while not ose_public_master:
        ose_public_master = \
          get_ose_public_master('xip')

    ose_admin_password = ''
    while not ose_admin_password:
        ose_admin_password = \
          get_ose_admin_password(cached_deploy_dict['ose_admin_password'])

    git_ssh_file = ''
    while not git_ssh_file:
        git_ssh_file = get_git_ssh_file(cached_deploy_dict['git_ssh_file'])

    # check to make sure the git ssh key exists and we can access it
    try:
        f = open(git_ssh_file, 'r')
        git_ssh_key = f.read()
        f.close()
    except:
        print("Could not read ssh key.")
        exit

    # No while because this parameter is optional.
    user_script_file = ''
    user_script_file = get_user_script_file(
        cached_deploy_dict['user_script_file'])

    # read import-is.sh

    f = open('resources/import-is.sh', 'r')
    import_is = f.read()
    import_is_b64 = base64.b64encode(import_is.encode('utf-8'))
    f.close

    # read optional openshift-config script if it was provided
    if user_script_file != "":
        try:
            f = open(user_script_file, 'r')
            user_script = f.read()
            user_script_b64 = base64.b64encode(user_script.encode('utf-8'))
            f.close
        except:
            print("Error opening user script file")
            sys.exit(2)

    if user_script_b64 == "":
        user_script_exec = ""
    else:
        # if there is a user script
        # adds this to the cloud-init script
        user_script_exec = \
            'source /root/deploy-ose/user-script.sh'

    # get the deploy script
    f = open('resources/deploy-ose.stache', 'r')
    script_template = f.read()
    f.close

    if ose_public_master == 'xip':
        ose_public_master = \
          '$(curl -s  http://169.254.169.254/latest/meta-data/public-hostname)'

    # dict of values that are passed to pystache for substitution
    # in deploy-ose.stache
    deploy_dict = {'rh_id': rh_id,
                   'rh_password': rh_password,
                   'reg_pool': reg_pool,
                   'git_ssh_key': git_ssh_key,
                   'ec2_key': ec2_key,
                   'user_script_exec': user_script_exec,
                   'user_script_b64': user_script_b64,
                   'import_is_b64': import_is_b64,
                   'ose_public_master': ose_public_master,
                   'ose_admin_password': ose_admin_password}

    # create a cache dictionary to write later
    deploy_cache = {'rh_id': rh_id,
                    'reg_pool': reg_pool,
                    'git_ssh_file': git_ssh_file,
                    'ec2_key': ec2_key,
                    'ose_admin_password': ose_admin_password,
                    'rh_password': rh_password,
                    'ec2_instance_tags': ec2_instance_tags,
                    'user_script_file': user_script_file,
                    'aws_profile_name': aws_profile_name,
                    'aws_subnet_id': aws_subnet_id}

    # write the settings to cache file
    f = open(os.environ['HOME'] + '/.osdd/deploy-ose.json', 'w')
    f.write(json.dumps(deploy_cache))
    f.close

    # secure the cache file as it contains passwords
    os.chmod(os.environ['HOME'] + '/.osdd/deploy-ose.json', 0o600)

    script = pystache.render(script_template, deploy_dict)
    f = open(os.environ['HOME'] + '/cloud-init.sh', 'w')
    f.write(script)
    f.close

    # print(ec2_instance_tags)

    # Boto 3
    session = boto3.session.Session(profile_name=aws_profile_name)
    ec2 = session.resource('ec2')

# create_ec2_instance(ec2, ec2_instance_tags,
#                        ec2_key, script, security_group_id, aws_subnet_id):
    if aws_subnet_id == 'default':
        create_ec2_instance(ec2,
                            ec2_instance_tags,
                            ec2_key,
                            script,
                            None,
                            None)
    else:
        create_ec2_instance(ec2,
                            ec2_instance_tags,
                            ec2_key,
                            script,
                            aws_security_group_id,
                            aws_subnet_id)

# out = ec2.Tag(, k, v)
#        print(out)

    # TODO get the id from json_result and tag the instance with the RH
    # username that created it

    print("")
    print("")
    print("")
    print("Settings cached in " + os.environ['HOME'] +
          '/.osdd/deploy-ose.json')
    print("")


if __name__ == "__main__":
    main()
