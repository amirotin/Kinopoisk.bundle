from os.path import split as split_path
import shutil, time


class Updater(object):
    def __init__(self, core, channel):
        self._core = core
        self._channel = channel
        self.identifier = self._core.identifier
        self.stage = self._core.storage.data_item_path('Stage')
        self.stage_path = self._core.storage.join_path(self.stage, self.identifier)
        self.plugins_path = self._core.storage.join_path(self._core.app_support_path, 'Plug-ins')
        self.bundle_name = self.splitall(self._core.bundle_path)[-1]
        self.inactive = self._core.storage.data_item_path('Deactivated')

        self.version_path = self._core.storage.join_path(self._core.bundle_path, 'Contents', 'VERSION')
        self.update_version = None

        self.stable_url = 'https://api.github.com/repos/amirotin/Kinopoisk.bundle/releases/latest'
        self.beta_url = 'https://api.github.com/repos/amirotin/Kinopoisk.bundle/git/refs/heads/master'

        self.archive_url = 'https://github.com/amirotin/Kinopoisk.bundle/archive/%s.zip'

    @classmethod
    def auto_update_thread(cls, core, pref):
        cls(core, pref['update_channel']).checker()
        core.runtime.create_timer(int(pref['update_interval'] or 1)*60, Updater.auto_update_thread, True, core.sandbox, True, core=core, pref=pref)

    def checker(self):
        self._core.log.debug('Check for channel %s updates', self._channel)

        url = getattr(self, '%s_url' % self._channel)
        req = self._core.networking.http_request(url)
        if req:
            git_data = self._core.data.json.from_string(req.content)
            map = {'beta': ('object', 'sha'), 'stable': {'tag_name'}}
            try:
                self.update_version = reduce(dict.get, map[self._channel], git_data)
                if not self.update_version:
                    self._core.log.debug('No updates for channel %s', self._channel)
                    return
                else:
                    self.update_version = self.update_version[:7]
                self._core.log.debug('Current actual version for channel %s = %s', self._channel, self.update_version)
                if self._core.storage.file_exists(self.version_path):
                    current_version = self._core.storage.load(self.version_path)
                    self._core.log.debug('Current actual version %s = %s', current_version, self.update_version)
                    if current_version == self.update_version:
                        self._core.log.debug('Current version is actual')
                        return

                self.install_zip_from_url(self.archive_url % self.update_version)
            except:
                self._core.log.error('Something goes wrong with updater', exc_info=True)

    @property
    def setup_stage(self):
        self._core.log.debug(u"Setting up staging area for {} at {}".format(self.identifier, self.stage_path))
        self._core.storage.remove_tree(self.stage_path)
        self._core.storage.make_dirs(self.stage_path)
        return self.stage_path

    def unstage(self):
        self._core.log.debug(u"Unstaging files for {} (removing {})".format(self.identifier, self.stage_path))
        self._core.storage.remove_tree(self.stage_path)

    def cleanup(self):
        inactive_path = self._core.storage.join_path(self.inactive, self.identifier)
        if self._core.storage.dir_exists(inactive_path):
            self._core.log.debug(u"Cleaning up after {} (removing {})".format(self.identifier, inactive_path))
            self._core.storage.remove_tree(inactive_path)

    def splitall(self, path):
        allparts = list()
        while True:
            parts = split_path(path)
            if parts[0] == path:  # sentinel for absolute paths
                allparts.insert(0, parts[0])
                break
            elif parts[1] == path: # sentinel for relative paths
                allparts.insert(0, parts[1])
                break
            else:
                path = parts[0]
                allparts.insert(0, parts[1])
        return allparts

    def copytree(self, src, dst):
        if not self._core.storage.file_exists(dst):
            self._core.log.debug(u"Creating dir at '{}'".format(dst))
            self._core.storage.make_dirs(dst)
        self._core.log.debug(u"Recursively copying contents of '{}' into '{}'".format(src, dst))
        for item in self._core.storage.list_dir(src):
            s = self._core.storage.join_path(src, item)
            d = self._core.storage.join_path(dst, item)
            if self._core.storage.dir_exists(s):
                self._core.log.debug(u"Copying '{}' into '{}'".format(s, d))
                self.copytree(s, d)
            else:
                self._core.log.debug(u"Copying with copy2 '{}' into '{}'".format(s, d))
                try:
                    shutil.copy2(s, d)
                except IOError as err:
                    self._core.log.error(u'Something wrong while file copy %s', err, exc_info=True)


    def install_zip_from_url(self, url):
        stage_path = self.setup_stage
        try:
            archive = self._core.data.archiving.zip_archive(self._core.networking.http_request(url).content)
        except:
            self._core.log.debug(u"Unable to download archive for {}".format(self.identifier))
            self.unstage()
            return False

        if archive.Test() != None:
            self._core.log.debug(u"The archive of {} is invalid - unable to continue".format(self.identifier))
            self.unstage()
            return False

        try:
            for archive_name in archive:
                parts = archive_name.split('/')[1:]

                if parts[0] == '' and len(parts) > 1:
                    parts = parts[1:]

                if len(parts) > 1 and parts[0] == 'Contents' and len(parts[-1]) > 0 and parts[-1][0] != '.':
                    file_path = self._core.storage.join_path(stage_path, *parts)
                    dir_path = self._core.storage.join_path(stage_path, *parts[:-1])

                    if not self._core.storage.dir_exists(dir_path):
                        self._core.storage.make_dirs(dir_path)
                    self._core.storage.save(file_path, archive[archive_name])
                    self._core.log.debug(u"Extracted {} to {} for {}".format(parts[-1], dir_path, self.identifier))
                else:
                    self._core.log.debug(U"Not extracting {}".format(archive_name))

            version_file_path = self._core.storage.join_path(self.stage, self.identifier, 'Contents', 'VERSION')
            if not self._core.storage.file_exists(version_file_path):
                self._core.storage.save(version_file_path, self.update_version)

        except:
            self._core.log.debug(u"Error extracting archive of {}".format(self.identifier))
            self.unstage()
            return False

        finally:
            archive.Close()

        plist_path = self._core.storage.join_path(self.stage, self.identifier, 'Contents', 'Info.plist')
        plist_data = self._core.storage.load(plist_path, binary=False)
        self._core.storage.save(plist_path, plist_data.replace('{{version}}',self.update_version), binary=False)
        try:
            self._core.storage.utime(self._core.plist_path, None)
        except:
            self._core.log.error('Error with utime function', exc_info=True)
        self.clean_old_bundle()
        if not self.activate():
            self._core.log.error(u"Unable to activate {}".format(self.identifier), exc_info=True)
            self.unstage()
            return False

        self.unstage()
        self.cleanup()

        return True

    def clean_old_bundle(self):
        stage_paths = list()
        root = self.bundle_name
        stage_path = self.stage_path.lstrip('\\\?')
        bundle_path = self._core.storage.abs_path(self._core.bundle_path).lstrip('\\\?')
        stage_index = int([i for i, l in enumerate(self.splitall(stage_path)) if l == self.identifier][1])
        bundle_index = int([i for i, l in enumerate(self.splitall(bundle_path)) if l == root][0])

        for dirpath, dirname, filenames in self._core.storage.walk(stage_path):
            for f in filenames:
                filepath = self._core.storage.join_path(stage_path, dirpath, f).lstrip('\\\?')
                filepaths = self.splitall(filepath)[stage_index:]
                stage_paths.append(self._core.storage.join_path(root, *filepaths[1:]))

        for dirpath, dirname, filenames in self._core.storage.walk(bundle_path):
            for f in filenames:
                filepath = self._core.storage.join_path(bundle_path, dirpath, f).lstrip('\\\?')
                filepaths = self.splitall(filepath)[bundle_index:]
                if self._core.storage.join_path(root, *filepaths[1:]) not in stage_paths:
                    old_item_path = self._core.storage.abs_path(self._core.storage.join_path(self.plugins_path, root, *filepaths[1:]))
                    self._core.log.debug(u"File/Folder does not exists in current Version.  Attempting to remove '{}'".format(old_item_path))
                    try:
                        if self._core.storage.dir_exists(old_item_path):
                            self._core.storage.remove_tree(old_item_path)
                        elif self._core.storage.file_exists(old_item_path):
                            self._core.storage.remove(old_item_path)
                        else:
                            self._core.log.warn(u"Cannot Remove Old '{}' file/folder, does not exists.".format(old_item_path))
                    except:
                        self._core.log.exception(u"Error Removing Old '{}' file/folder".format(old_item_path))

    def activate(self, fail_count=0):
        final_path = self._core.storage.join_path(self.plugins_path, self.bundle_name)

        if not self._core.storage.dir_exists(self.stage_path):
            self._core.log.debug(u"Unable to find stage for {}".format(self.identifier))
            return False

        self._core.log.debug(u"Activating a new installation of {}".format(self.identifier))
        try:
            if not self._core.storage.dir_exists(final_path):
                self._core.storage.rename(self.stage_path, final_path)
            else:
                self.copytree(self.stage_path, final_path)
        except:
            self._core.log.exception(u"Unable to activate {} at {}".format(self.identifier, final_path))
            if fail_count < 5:
                self._core.log.info("Waiting 2s and trying again")
                time.sleep(2)
                return self.activate(fail_count + 1)
            else:
                self._core.log.info("Too many failures - returning")
                return False
        return True