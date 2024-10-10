#!/usr/bin/python

import asyncio

from ansible.module_utils.basic import AnsibleModule
from catamaran.github import GithubEnvVars
from catamaran.ansible import AnsibleResult
from catamaran import delete_image


def my_ansible_function(name, message="Hello"):
    return f"{message}, {name}!"


async def run_module():
    module_args = dict(
        image=dict(type="str", required=True),
        owner=dict(type="str", required=True),
        tag=dict(type="str", required=False),
        state=dict(type="str", required=False),
        token=dict(type="str", required=True),
    )

    result = AnsibleResult()
    env_vars = GithubEnvVars()

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    image_name = module.params["image"]
    owner = module.params["owner"]
    tag = module.params.get("tag", None)
    state: str = module.params.get("state", "present")

    try:
        if state != "absent":
            result.skipped = True
            result.msg = "State is not absent."
            module.exit_json(**result.to_dict())

        if not env_vars.is_delete_event():
            result.msg = "Event is not a ref delete event"
            result.skipped = True
            module.exit_json(**result.to_dict())

        if tag is None:
            tag = env_vars.ref_name()

        await delete_image(
            tag,
            image_name,
            owner,
            token=module.params["token"],
        )
        result.msg = f"Image {image_name} deleted."

        if module.check_mode:
            module.exit_json(**result.to_dict())

        result.changed = True
        module.exit_json(**result.to_dict())

    except Exception as e:
        module.fail_json(msg=f"Error parsing event: {e}")


async def main():
    await run_module()


if __name__ == "__main__":
    asyncio.run(main())
