#!/usr/bin/python

import socket
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: z_sign
short_description: Generate and execute certificate signing commands for shards and replicas
description:
  - This module generates and executes certificate signing commands for a specified domain, token, number of shards, and replicas.
  - Commands are executed using the `z cert sign` tool, which must be available on the target system.
  - Each shard and replica gets a unique certificate command with associated domain and IP addresses.
version_added: "1.0.0"
options:
  domain:
    description:
      - The base domain name used for generating shard and replica subdomains.
      - Example: `example.com` results in subdomains like `shard-a.example.com`.
    required: true
    type: str
  token:
    description:
      - A unique token used in certificate names for identification.
      - Example: `abc123` results in certificate names like `zygote-abc123-a`.
    required: true
    type: str
  num_shards:
    description:
      - The number of shards to generate certificates for.
      - Each shard is identified by a lowercase letter (1=a, 2=b, etc.).
      - Must be a positive integer.
    required: true
    type: int
  num_replicas:
    description:
      - The number of replicas per shard to generate certificates for.
      - Must be a non-negative integer.
    required: true
    type: int
  tenant:
    description:
      - The tenant name used as a prefix for certificate names.
      - If not specified, defaults to 'zygote'.
      - Example: `mytenant` results in certificate names like `mytenant-abc123-a`.
    required: false
    type: str
    default: zygote
  node_type:
    description:
      - The node type used in subdomain generation.
      - If not specified, defaults to 'shard'.
      - Example: `node` results in subdomains like `node-a.example.com`.
    required: false
    type: str
    default: shard
author:
  - Hamed Ghasemzadeh (hg@evgnomon.org)
notes:
  - This module executes commands using the `z cert sign` tool. Ensure it is installed and accessible on the target system.
  - Domain names are resolved to IP addresses using Python's socket module for DNS resolution.
  - In check mode, the module returns the list of commands without executing them.
  - If any command fails (non-zero return code), the module fails unless configured otherwise.
requirements:
  - python >= 3.6
  - z cert sign tool
seealso:
  - name: Ansible command module
    description: Details on how commands are executed
    link: https://docs.ansible.com/ansible/latest/collections/ansible/builtin/command_module.html
"""

EXAMPLES = r"""
# Generate and execute certificate commands for 3 shards with 2 replicas each
- name: Generate and execute certificate commands
  evgnomon.catamaran.z_sign:
    domain: example.com
    token: abc123
    num_shards: 3
    num_replicas: 2
  register: cert_result

# Generate certificates with custom tenant and node type
- name: Generate certificates with custom tenant and node type
  evgnomon.catamaran.z_sign:
    domain: example.com
    token: abc123
    num_shards: 2
    num_replicas: 1
    tenant: mytenant
    node_type: node
  register: cert_result

# Display the execution results
- name: Show command execution results
  ansible.builtin.debug:
    msg: "{{ cert_result.results }}"

# Run in check mode to preview commands without execution
- name: Preview certificate commands
  evgnomon.catamaran.z_sign:
    domain: example.com
    token: abc123
    num_shards: 3
    num_replicas: 2
  check_mode: yes
  register: cert_result
"""

RETURN = r"""
commands:
  description: A list of certificate signing commands that were generated and (if not in check mode) executed.
  type: list
  elements: str
  returned: always
  sample:
    - "z cert sign --name zygote-abc123-a --name shard-a.example.com --ip 127.0.0.1 --ip 192.168.1.100"
    - "z cert sign --name zygote-abc123-a-1 --name shard-a-1.example.com --ip 127.0.0.1 --ip 192.168.1.101"
    - "z cert sign --name mytenant-abc123-a --name node-a.example.com --ip 127.0.0.1 --ip 192.168.1.100"
results:
  description: A list of dictionaries containing the execution results for each command (empty in check mode).
  type: list
  elements: dict
  returned: always
  contains:
    cmd:
      description: The command that was executed.
      type: str
    rc:
      description: The return code of the command (0 indicates success).
      type: int
    stdout:
      description: The standard output of the command.
      type: str
    stderr:
      description: The standard error of the command.
      type: str
  sample:
    - cmd: "z cert sign --name zygote-abc123-a --name shard-a.example.com --ip 127.0.0.1 --ip 192.168.1.1"
      rc: 0
      stdout: "Certificate signed successfully"
      stderr: ""
changed:
  description: Indicates if the module made changes by executing commands (always true unless in check mode).
  type: bool
  returned: always
  sample: true
msg:
  description: Error message if the module fails.
  type: str
  returned: on failure
  sample: "Failed to execute command: z cert sign ... (rc=1)"
"""


def num_to_letter(num):
    """Convert number to lowercase letter (1->a, 2->b, etc.)"""
    return chr(96 + num)


def resolve_domain_ip(domain):
    """Resolve domain name to IP address using Python's socket module"""
    try:
        # Get all IP addresses for the domain
        ip_addresses = socket.getaddrinfo(
            domain, None, socket.AF_INET, socket.SOCK_STREAM
        )
        # Return the first IPv4 address
        for addr_info in ip_addresses:
            if addr_info[0] == socket.AF_INET:
                return addr_info[4][0]
        # If no IPv4 found, return the first available
        if ip_addresses:
            return ip_addresses[0][4][0]
        else:
            raise ValueError(f"Unable to resolve domain '{domain}' to any IP address")
    except socket.gaierror as e:
        raise ValueError(f"DNS resolution failed for domain '{domain}': {e}")
    except Exception as e:
        raise ValueError(f"Error resolving domain '{domain}': {e}")


def run_module():
    # Define module arguments
    module_args = dict(
        domain=dict(type="str", required=True),
        token=dict(type="str", required=True),
        num_shards=dict(type="int", required=True),
        num_replicas=dict(type="int", required=True),
        tenant=dict(type="str", required=False, default="zygote"),
        node_type=dict(type="str", required=False, default="shard"),
    )

    # Initialize result dictionary
    result = dict(changed=False, commands=[], results=[], msg="")

    # Initialize Ansible module
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    # Get parameters
    domain = module.params["domain"]
    token = module.params["token"]
    num_shards = module.params["num_shards"]
    num_replicas = module.params["num_replicas"]
    tenant = module.params.get("tenant")
    node_type = module.params.get("node_type")

    # Validate numeric inputs
    if num_shards <= 0 or num_replicas < 0:
        module.fail_json(
            msg="num_shards must be positive and num_replicas must be non-negative"
        )

    try:
        # Generate certificates for each shard
        result["commands"] = []
        result["results"] = []
        for shard in range(1, num_shards + 1):
            shard_letter = num_to_letter(shard)

            # Generate certificate for shard without replica suffix
            shard_name = f"{tenant}-{token}-{shard_letter}"
            replica_domain = f"{node_type}-{shard_letter}.{domain}"
            try:
                resolved_ip = resolve_domain_ip(replica_domain)
            except ValueError as e:
                result["msg"] = (
                    f"Failed to resolve IP for shard domain {replica_domain}: {e}"
                )
                module.fail_json(**result)
            command = (
                f"z cert sign --name {shard_name} --name {replica_domain} "
                f"--ip 127.0.0.1 --ip {resolved_ip}"
            )
            result["commands"].append(command)

            # Generate certificates for replicas
            for replica in range(1, num_replicas):
                replica_name = f"{tenant}-{token}-{shard_letter}-{replica}"
                replica_domain = f"{node_type}-{shard_letter}-{replica}.{domain}"
                try:
                    resolved_ip = resolve_domain_ip(replica_domain)
                except ValueError as e:
                    result["msg"] = (
                        f"Failed to resolve IP for replica domain {replica_domain}: {e}"
                    )
                    module.fail_json(**result)
                command = (
                    f"z cert sign --name {replica_name} --name {replica_domain} "
                    f"--ip 127.0.0.1 --ip {resolved_ip}"
                )
                result["commands"].append(command)

        # Set changed to True since commands would be generated/executed
        result["changed"] = True

        # In check mode, return without executing
        if module.check_mode:
            module.exit_json(**result)

        # Execute each command
        for command in result["commands"]:
            rc, stdout, stderr = module.run_command(command, use_unsafe_shell=True)
            result["results"].append(
                {
                    "cmd": command,
                    "rc": rc,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            )
            if rc != 0:
                result["msg"] = (
                    f"Failed to execute command: {command} (rc={rc}, stderr={stderr})"
                )
                module.fail_json(**result)

        # Exit with success
        module.exit_json(**result)

    except Exception as e:
        result["msg"] = f"Error generating or executing certificate commands: {str(e)}"
        module.fail_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
