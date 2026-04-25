Place your goal audio files here.

Supported formats: MP3, OGG, WAV (anything pygame.mixer can decode).

Expected filenames (matching goalsense/config.py defaults):
  goal.mp3          – played when the player scores
  opponent_goal.mp3 – played when the opponent scores (optional)

You can override the paths in goalsense/config.py:
  PLAYER_GOAL_SOUND   = "sounds/my_song.mp3"
  OPPONENT_GOAL_SOUND = "sounds/boo.mp3"   # leave empty string to disable
