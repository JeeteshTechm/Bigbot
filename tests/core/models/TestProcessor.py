import unittest
from unittest.mock import MagicMock

class TestSkillProcessor(unittest.TestCase):

    def test_on_process(self):
        binder = MagicMock()
        input = MagicMock()
        skill_processor = SkillProcessor()

        # Test if the code handles a call to a skill block and move to the next block if a connection is provided.
        block_object = MagicMock()
        type(block_object).process = MagicMock(return_value=MagicMock(connection='some_id'))
        binder.on_load_state.return_value = MagicMock(skill='some_skill', block_id='some_block_id')
        binder.on_save_state = MagicMock()
        binder.post_message = MagicMock()
        binder.on_get_skill = MagicMock()
        skill_processor.get_block_by_id = MagicMock(return_value=block_object)
        skill_processor.on_process(binder, input)

        # Assert if the binder's state is saved
        binder.on_save_state.assert_called()
        # Assert if the next block is returned correctly
        skill_processor.get_block_by_id.assert_called_with(binder, 'some_skill', 'some_block_id')
        # Assert if the post_message is not called
        binder.post_message.assert_not_called()

        # Test if the code handles a call to a prompt block and post message
        block_object = MagicMock()
        type(block_object).process = MagicMock(return_value=MagicMock(connection=None))
        binder.on_load_state.return_value = MagicMock(skill='some_skill', block_id='some_block_id')
        binder.on_save_state = MagicMock()
        binder.post_message = MagicMock()
        binder.on_get_skill = MagicMock()
        skill_processor.get_block_by_id = MagicMock(return_value=block_object)
        skill_processor.on_process(binder, input)

        # Assert if the binder's state is saved
        binder.on_save_state.assert_called()
        # Assert if the post_message is called
        binder.post_message.assert_called()
        # Assert if the on_get_skill is not called
        binder.on_get_skill.assert_not_called()

if __name__ == '__main__':
    unittest.main()
