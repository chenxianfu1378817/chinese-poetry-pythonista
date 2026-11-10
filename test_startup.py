import ast,hashlib,importlib.util,io,json,shutil,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        shutil.copytree(ROOT/'data',self.root/'data')
        (self.root/'main.py').write_text('OLD_LAUNCHER = True\n')
        user=self.root/'user_data';user.mkdir()
        self.profile=b'{"favorites":["kept"],"notes":{"kept":"untouched"}}'
        (user/'profile.json').write_bytes(self.profile)
    def tearDown(self):self.temp.cleanup()
    def launcher(self):
        spec=importlib.util.spec_from_file_location('launcher_test',ROOT/'main.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.ROOT=str(self.root);module.USER=str(self.root/'user_data')
        return module
    def test_previous_incomplete_start_rolls_back(self):
        user=self.root/'user_data';(user/'active.json').write_text('{"version":"1.1.0"}')
        (user/'startup_state.json').write_text('{"version":"1.1.0","phase":"starting"}')
        module=self.launcher()
        with patch.object(module,'load',return_value='safe-view') as load:
            self.assertEqual(module.main(),'safe-view');load.assert_called_once_with(str(self.root))
        self.assertFalse((user/'active.json').exists())
        self.assertEqual((user/'profile.json').read_bytes(),self.profile)
    def test_python_start_failure_is_recorded_and_update_disabled(self):
        folder=self.root/'releases/1.1.1/poetry_app';folder.mkdir(parents=True);(folder/'app.py').write_text('x=1')
        (self.root/'user_data/active.json').write_text('{"version":"1.1.1"}')
        module=self.launcher()
        with patch.object(module,'load',side_effect=RuntimeError('test-start-error')):self.assertIsNone(module.main())
        self.assertIn('test-start-error',(self.root/'user_data/startup_error.txt').read_text())
        self.assertFalse((self.root/'user_data/active.json').exists())
        self.assertEqual((self.root/'user_data/profile.json').read_bytes(),self.profile)
    def test_broken_bundled_110_is_not_reopened(self):
        package=self.root/'poetry_app';package.mkdir();(package/'core.py').write_text("VERSION = '1.1.0'")
        (self.root/'user_data/active.json').write_text('{"version":"1.1.0"}')
        module=self.launcher()
        with patch.object(module,'load') as load:
            self.assertIsNone(module.main());load.assert_not_called()
        self.assertEqual((self.root/'user_data/profile.json').read_bytes(),self.profile)
    def test_bad_previous_version_is_skipped(self):
        folder=self.root/'releases/1.1.0/poetry_app';folder.mkdir(parents=True);(folder/'app.py').write_text('x=1')
        user=self.root/'user_data'
        (user/'active.json').write_text('{"version":"1.1.1","previous_version":"1.1.0"}')
        (user/'startup_state.json').write_text('{"version":"1.1.1","phase":"starting"}')
        module=self.launcher()
        with patch.object(module,'load',return_value='safe-view') as load:
            self.assertEqual(module.main(),'safe-view');load.assert_called_once_with(str(self.root))
    def test_production_code_has_no_unsafe_runtime_bridges(self):
        for path in (ROOT/'poetry_app').glob('*.py'):
            tree=ast.parse(path.read_text())
            imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
            imports += [name.name for n in ast.walk(tree) if isinstance(n,ast.Import) for name in n.names]
            self.assertNotIn('objc_util',imports,path.name)
            self.assertNotIn('ctypes',imports,path.name)
if __name__=='__main__':unittest.main()
