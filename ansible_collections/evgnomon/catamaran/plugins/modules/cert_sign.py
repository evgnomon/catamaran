#!/usr/bin/python

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
author:
  - Hamed Ghasemzadeh (hg@evgnomon.org)
notes:
  - This module executes commands using the `z cert sign` tool. Ensure it is installed and accessible on the target system.
  - Commands include a `dig +short` subshell to resolve IP addresses, requiring the `dig` command to be available.
  - In check mode, the module returns the list of commands without executing them.
  - If any command fails (non-zero return code), the module fails unless configured otherwise.
requirements:
  - python >= 3.6
  - z cert sign tool
  - dig command
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
    - "z cert sign --name zygote-abc123-a --name shard-a.example.com --ip 127.0.0.1 --ip $(dig +short shard-a.example.com)"
    - "z cert sign --name zygote-abc123-a-1 --name shard-a-1.example.com --ip 127.0.0.1 --ip $(dig +short shard-a-1.example.com)"
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


def run_module():
    # Define module arguments
    module_args = dict(
        domain=dict(type="str", required=True),
        token=dict(type="str", required=True),
        num_shards=dict(type="int", required=True),
        num_replicas=dict(type="int", required=True),
    )

    # Initialize result dictionary
    result = dict(changed=False, commands=[], results=[], msg="")

    # Initialize Ansible module
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    # Get module parameters
    domain = module.params["domain"]
    token = module.params["token"]
    num_shards = module.params["num_shards"]
    num_replicas = module.params["num_replicas"]

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
            shard_name = f"zygote-{token}-{shard_letter}"
            replica_domain = f"shard-{shard_letter}.{domain}"
            command = (
                f"z cert sign --name {shard_name} --name {replica_domain} "
                f"--ip 127.0.0.1 --ip $(dig +short {replica_domain})"
            )
            result["commands"].append(command)

            # Generate certificates for replicas
            for replica in range(1, num_replicas):
                replica_name = f"zygote-{token}-{shard_letter}-{replica}"
                replica_domain = f"shard-{shard_letter}-{replica}.{domain}"
                command = (
                    f"z cert sign --name {replica_name} --name {replica_domain} "
                    f"--ip 127.0.0.1 --ip $(dig +short {replica_domain})"
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
            result["results"].append({
                "cmd": command,
                "rc": rc,
                "stdout": stdout,
                "stderr": stderr,
            })
            if rc != 0:
                module.fail_json(
                    msg=f"Failed to execute command: {command} (rc={rc}, stderr={stderr})",
                    **result,
                )

        # Exit with success
        module.exit_json(**result)

    except Exception as e:
        module.fail_json(
            msg=f"Error generating or executing certificate commands: {str(e)}",
            **result,
        )


def main():
    run_module()


if __name__ == "__main__":
    main()
