"""VIS-16 / JR-17: a project Kel creates gets a short, human name and a tidy folder."""
import tempfile
import unittest
from pathlib import Path

from kel.projects import new_project_folder, readable_project_name


class ReadableProjectNameTests(unittest.TestCase):
    def test_uses_the_works_own_short_title(self):
        self.assertEqual(readable_project_name('I want to create a little app that mutes my mic',
                                               'Mic mute toggle app'), 'Mic mute toggle app')

    def test_ignores_a_title_that_is_only_the_request_cut_off(self):
        text = 'I want to create a little app that allows me to control my microphone'
        self.assertEqual(readable_project_name(text, 'I want to create a little app that…'), 'Little app')

    def test_takes_the_subject_of_the_request(self):
        self.assertEqual(readable_project_name('Build me a to-do list web app with dark mode'), 'To-do list web app')
        self.assertEqual(readable_project_name('Can you please make a tiny game for my kids'), 'Tiny game')
        self.assertEqual(readable_project_name(''), 'New project')

    def test_stays_short_and_unique(self):
        name = readable_project_name('create ' + 'verylongword ' * 20)
        self.assertLessEqual(len(name), 40)
        self.assertEqual(readable_project_name('create a tiny game', taken=['Tiny game', 'tiny game 2']), 'Tiny game 3')


class NewProjectFolderTests(unittest.TestCase):
    def test_names_the_folder_after_the_project_and_avoids_clashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(new_project_folder('Mic mute toggle app', tmp), Path(tmp) / 'mic-mute-toggle-app')
            (Path(tmp) / 'mic-mute-toggle-app').mkdir()
            self.assertEqual(new_project_folder('Mic mute toggle app', tmp), Path(tmp) / 'mic-mute-toggle-app-2')
            self.assertEqual(new_project_folder("Brother's site!", tmp).name, 'brother-s-site')


if __name__ == '__main__':
    unittest.main()
