import json
import time

from . import Log
from . import Block
from .Block import get_block_by_id, InputBlock, PromptBlock
from .Statement import OutputStatement, InputStatement
# from bigbot.runtime import RustTokioRuntime

class BaseProcessor:
    def __init__(self):
        pass

    def on_process(self, binder, input):
        pass

    def get_context(self):
        return {"user": {"first_name": "Bob"}}

async def cancel_skill(binder):
    try:
        state = await binder.on_load_state()
        state.skill = None
        state.block_id = None
        state.data = {}
        state.extra = {}
        await binder.on_save_state(state.serialize())

        output = OutputStatement(await binder.on_load_state().operator_id)
        output.append_text("Your request has been cancelled.")
        await binder.post_message(output)
    except Exception as e:
        Log.error("cancel_skill", str(e))

class SkillProcessor(BaseProcessor):
    async def on_process(self, binder, input, is_start=False):
        runtime = RustTokioRuntime()
        try:
            state = await binder.on_load_state()
            skill = state.skill
            block_id = state.block_id

            block_object = await runtime.block_on(get_block_by_id(binder, skill, block_id))

            if isinstance(block_object, InputBlock):
                block_result = await runtime.block_on(block_object.process(binder, state.operator_id, input))
            else:
                block_result = await runtime.block_on(block_object.process(binder, state.operator_id))

            if block_result.connection is None:
                state.skill = None
                state.block_id = None
                state.data = {}
                state.extra = {}
                await binder.on_save_state(state.serialize())
                Log.debug("SkillProcessor", "skill completed!")
                post_skill_package = block_result.post_skill()
                post_skill = await runtime.block_on(binder.on_get_skill(post_skill_package))
                if post_skill:
                    # start new chain skill
                    post_skill_input = InputStatement(state.user_id)
                    post_skill_input.input = post_skill
                    await StartSkill().on_process(binder, post_skill_input)
            else:
                state.block_id = block_result.connection
                await binder.on_save_state(state.serialize())
                next_block = await runtime.block_on(get_block_by_id(binder, skill, block_result.connection))
                if not isinstance(next_block, InputBlock):
                    await self.on_process(binder, input)
        except Exception as e:
            Log.error("SkillProcessor", str(e))
        finally:
            del runtime

async def standard_input(binder, input):
    runtime = RustTokioRuntime()
    try:
        output = OutputStatement(await binder.on_load_state().operator_id)
        final_output = await runtime.block_on(binder.on_standard_input(input, output))
        if final_output:
            await binder.post_message(final_output)
    except Exception as e:
        Log.error("standard_input", str(e))
    finally:
        del runtime

class StartSkill(BaseProcessor):
    async def on_process(self, binder, input):
        runtime = RustTokioRuntime()
        try:
            skill = input.input

            state = await binder.on_load_state()
            state.skill = skill
            state.block_id = skill["start"]
            await binder.on_save_state(state.serialize())

            await SkillProcessor().on_process(binder, input, True)
        except Exception as e:
            Log.error("StartSkill", str(e))
        finally:
            del runtime
