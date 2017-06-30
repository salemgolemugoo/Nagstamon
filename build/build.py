#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Nagstamon - Nagios status monitor for your desktop
# Copyright (C) 2008-2016 Henri Wahl <h.wahl@ifw-dresden.de> et al.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

import platform
import os, os.path
import sys
import shutil
import subprocess
import zipfile
import glob
import time
from distutils.spawn import find_executable

CURRENT_DIR = os.getcwd()
NAGSTAMON_DIR = os.path.normpath('{0}{1}..{1}'.format(CURRENT_DIR, os.sep))
sys.path.append(NAGSTAMON_DIR)

SCRIPTS_DIR = '{0}{1}scripts-{2}.{3}'.format(CURRENT_DIR, os.sep, sys.version_info.major, sys.version_info.minor)

from Nagstamon.Config import AppInfo

VERSION = AppInfo.VERSION
ARCH = platform.architecture()[0][0:2]
ARCH_OPTS = {'32': ('win32', 'win32', '', 'x86'),
             '64': ('win-amd64', 'amd64', '(X86)', 'x64')}
PYTHON_VERSION = '{0}.{1}'.format(sys.version_info[0],
                                  sys.version_info[1])


def winmain():
    """
        execute steps necessary for compilation of Windows binaries and setup.exe
    """
    # InnoSetup does not like VersionInfoVersion with letters, only 0.0.0.0 schemed numbers
    if 'alpha' in VERSION.lower() or 'beta' in VERSION.lower() or 'rc' in VERSION.lower() or '-' in VERSION.lower():
        VERSION_IS = VERSION.replace('alpha', '').replace('beta', '').replace('rc', '').replace('-', '.').replace('..', '.')
        VERSION_IS = VERSION_IS.split('.')
        version_segments = list()
        for part in VERSION_IS:
            if len(part) < 4:
                version_segments.append(part)
            else:
                version_segments.append(part[0:4])
                version_segments.append(part[4:])
        VERSION_IS = '.'.join(version_segments)
    else:
        VERSION_IS = VERSION

    print('VERSION_IS:', VERSION_IS)

    ISCC = r'{0}{1}Inno Setup 5{1}iscc.exe'.format(os.environ['PROGRAMFILES{0}'.format(ARCH_OPTS[ARCH][2])], os.sep)
    DIR_BUILD_EXE = '{0}{1}exe.{2}-{3}'.format(CURRENT_DIR, os.sep, ARCH_OPTS[ARCH][0], PYTHON_VERSION)
    DIR_BUILD_NAGSTAMON = '{0}{1}Nagstamon-{2}-win{3}'.format(CURRENT_DIR, os.sep, VERSION, ARCH)
    FILE_ZIP = '{0}.zip'.format(DIR_BUILD_NAGSTAMON)

    # clean older binaries
    for file in (DIR_BUILD_EXE, DIR_BUILD_NAGSTAMON, FILE_ZIP):
        if os.path.exists(file):
            try:
                shutil.rmtree(file)
            except:
                os.remove(file)

    # go one directory up and run setup.py
    os.chdir('{0}{1}..'.format(CURRENT_DIR, os.sep))
    subprocess.call([sys.executable, 'setup.py', 'build_exe'], shell=True)
    os.rename(DIR_BUILD_EXE, DIR_BUILD_NAGSTAMON)

    # The following is a workaround for a behaviour of Python 3.6 + cx_freeze 5.0.1
    # where ALL reachable files are copied into build directory thus blowing it
    # to 170 MB instead of 60
    #
    # The dirty workaround consists of starting nagstamon.exe and use the
    # file-locking of Windows to delete everything unnecessary but keep the
    # locked and needed files
    #
    # If someone has a better fix let me know.

    # run nagstamon.exe and wait some seconds to give GUI time to come up
    subprocess.Popen('{0}/nagstamon.exe'.format(DIR_BUILD_NAGSTAMON))
    time.sleep(5)

    # go to Nagstamon build directory and start the deleting
    os.chdir(DIR_BUILD_NAGSTAMON)

    for directory in ['imageformats',\
                      'mediaservice',\
                      'platforms',\
                      'PyQt5/uic',\
                      'PyQt5/Qt/qml/',\
                      'PyQt5/Qt/resources/',\
                      'PyQt5/Qt/translations/',\
                      ]:
        try:
            shutil.rmtree('./{0}'.format(directory))
        except Exception as err:
            print(err)

    os.chdir('{0}/PyQt5'.format(DIR_BUILD_NAGSTAMON))

    for pyd_file in glob.iglob('*.pyd'):
        try:
            os.remove(pyd_file)
        except Exception as err:
            print(err)

    os.chdir('{0}/PyQt5/Qt/bin'.format(DIR_BUILD_NAGSTAMON))

    for pyd_file in glob.iglob('*'):
        try:
            os.remove(pyd_file)
        except Exception as err:
            print(err)

    os.chdir('{0}/PyQt5/Qt/plugins'.format(DIR_BUILD_NAGSTAMON))

    for pyd_file in glob.iglob('*'):
        try:
            shutil.rmtree(pyd_file)
        except Exception as err:
            print(err)

    # after cleaning start zipping and setup.exe-building - go back to original directory
    os.chdir(CURRENT_DIR)

    # create .zip file
    if os.path.exists(DIR_BUILD_NAGSTAMON):
        zip_archive = zipfile.ZipFile(FILE_ZIP, mode='w', compression=zipfile.ZIP_DEFLATED)
        zip_archive.write(os.path.basename(DIR_BUILD_NAGSTAMON))
        for root, dirs, files in os.walk(os.path.basename(DIR_BUILD_NAGSTAMON)):
            for file in files:
                zip_archive.write('{0}{1}{2}'.format(root, os.sep, file ))

    # execute InnoSetup with many variables set by ISCC.EXE outside .iss file
    subprocess.call([ISCC,
                     r'/Dsource={0}'.format(DIR_BUILD_NAGSTAMON),
                     r'/Dversion_is={0}'.format(VERSION_IS),
                     r'/Dversion={0}'.format(VERSION),
                     r'/Darch={0}'.format(ARCH),
                     r'/Darchs_allowed={0}'.format(ARCH_OPTS[ARCH][3]),
                     r'/Dresources={0}{1}resources'.format(DIR_BUILD_NAGSTAMON, os.sep),
                     r'/O{0}'.format(CURRENT_DIR),
                     r'{0}{1}windows{1}nagstamon.iss'.format(CURRENT_DIR, os.sep)], shell=True)


def macmain():
    """
        execute steps necessary for compilation of MacOS X binaries and .dmg file
    """
    # go one directory up and run pyinstaller
    os.chdir('{0}{1}..'.format(CURRENT_DIR, os.sep))

    # find pyinstaller executable
    pyinstaller_bin = find_executable('pyinstaller')

    if not pyinstaller_bin:
        print('PyInstaller is not found. Install it with "pip install PyInstaller"')
        exit

    # create one-file .app bundle by pyinstaller
    subprocess.call([os.path.abspath(pyinstaller_bin),
                     '--noconfirm',
                     '--add-data=Nagstamon/resources:Nagstamon/resources',
                     '--icon=Nagstamon/resources/nagstamon.icns',
                     '--name=Nagstamon',
                     '--osx-bundle-identifier=de.ifw-dresden.nagstamon',
                     '--windowed',
                     '--onefile',
                     'nagstamon.py'])

    # go back to build directory
    os.chdir(CURRENT_DIR)
    
    # create staging DMG folder for later compressing of DMG
    shutil.rmtree('Nagstamon {0} Staging DMG'.format(VERSION), ignore_errors=True)
    
    # copy app bundle folder
    shutil.move('../dist/Nagstamon.app', 'Nagstamon {0} Staging DMG/Nagstamon.app'.format(VERSION))
    
    # cleanup before new images get created
    for dmg_file in glob.iglob('*.dmg'):
        os.unlink(dmg_file)
        
    # create DMG
    subprocess.call(['hdiutil create -srcfolder "Nagstamon {0} Staging DMG" -volname "Nagstamon {0}" -fs HFS+ -format UDRW -size 100M "Nagstamon {0} uncompressed.dmg"'.format(VERSION)], shell=True)

    # Compress DMG
    subprocess.call(['hdiutil convert "Nagstamon {0} uncompressed".dmg -format UDZO -imagekey zlib-level=9 -o "Nagstamon {0}.dmg"'.format(VERSION)], shell=True)

    # Delete uncompressed DMG file as it is no longer needed
    os.unlink('Nagstamon {0} uncompressed.dmg'.format(VERSION))


def debmain():
    shutil.rmtree(SCRIPTS_DIR, ignore_errors=True)
    shutil.rmtree('{0}{1}.pybuild'.format(CURRENT_DIR, os.sep), ignore_errors=True)
    shutil.rmtree('{0}{1}debian'.format(NAGSTAMON_DIR, os.sep), ignore_errors=True)

    os.chdir(NAGSTAMON_DIR)

    # masquerade .py file as .py-less
    shutil.copyfile('nagstamon.py', 'nagstamon')

    shutil.copytree('{0}{1}debian{1}'.format(CURRENT_DIR, os.sep), '{0}{1}debian'.format(NAGSTAMON_DIR, os.sep))

    os.chmod('{0}{1}debian{1}rules'.format(CURRENT_DIR, os.sep),0o755)

    subprocess.call(['fakeroot', 'debian/rules', 'build'])

    subprocess.call(['fakeroot', 'debian/rules', 'binary'])

    # copy .deb file to current directory
    for deb in glob.iglob('../nagstamon*.deb'):
        shutil.move(deb, CURRENT_DIR)


def rpmmain():
    """
        create .rpm file via setup.py bdist_rpm - most settings are in setup.py
    """

    os.chdir(NAGSTAMON_DIR)

    # masquerade .py file as .py-less
    shutil.copyfile('nagstamon.py', 'nagstamon')

    # workaround for manpage gzipping bug in bdist_rpm
    import gzip
    man = open('Nagstamon/resources/nagstamon.1', 'rb')
    mangz = gzip.open('Nagstamon/resources/nagstamon.1.gz', 'wb')
    mangz.writelines(man)
    mangz.close()
    man.close()

    # run setup.py for rpm creation
    subprocess.call(['python3', 'setup.py', 'bdist_rpm'], shell=False)


DISTS = {
    'debian': debmain,
    'Ubuntu': debmain,
    'LinuxMint': debmain,
    'fedora': rpmmain
}


if __name__ == '__main__':
    if platform.system() == 'Windows':
        winmain()
    elif platform.system() == 'Darwin':
        macmain()
    else:
        dist = platform.dist()[0]
        if dist in DISTS:
            DISTS[dist]()
        else:
            print('Your system is not supported for automated build yet')
