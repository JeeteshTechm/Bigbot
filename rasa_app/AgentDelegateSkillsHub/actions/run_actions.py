import subprocess

class ActionServerManager:
    def stop_action_server(self):
        try:
            # Stop the running Rasa action server using subprocess
            subprocess.Popen(['pkill', '-f', 'rasa run actions'])
            
            return ({'message': 'Rasa action server stopped successfully!'})
        except Exception as e:
            return ({'error': str(e)}), 500

    def start_action_server(self):
        try:
            # Stop the existing Rasa action server
            self.stop_action_server()

            # Start the new Rasa action server using subprocess
            subprocess.Popen(['rasa', 'run', 'actions'])
            
            return ({'message': 'Rasa action server started successfully!'})
        except Exception as e:
            return ({'error': str(e)}), 500
