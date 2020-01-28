# Copyright (c) 2019, IRIS-HEP
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import os
import pickle
import zipfile
from collections import namedtuple
from tempfile import TemporaryDirectory

from func_adl.ast import ast_hash
from func_adl_xAOD.backend.xAODlib.atlas_xaod_executor import atlas_xaod_executor
from qastle import text_ast_to_python_ast
from func_adl_xAOD.backend.util_LINQ import find_dataset, extract_dataset_info
from func_adl_uproot.translation import generate_python_source

GeneratedFileResult = namedtuple('GeneratedFileResult', 'hash output_dir')


class GenerateCodeException(BaseException):
    """Custom exception for top level code generation exceptions"""

    def __init__(self, message: str):
        BaseException.__init__(self, message)


class AstTranslater:
    def __init__(self, target_backend):
        assert target_backend in ['xAOD', 'uproot']
        self.target_backend = target_backend

    def zipdir(self, path: str, zip_handle: zipfile.ZipFile) -> None:
        """Given a `path` to a directory, zip up its contents into a zip file.

        Arguments:
            path        Path to a local directory. The contents will be put into the zip file
            zip_handle  The zip file handle to write into.
        """
        for root, _, files in os.walk(path):
            for file in files:
                zip_handle.write(os.path.join(root, file), file)

    def get_generated_uproot(self, a, cache_path: str):
        # Calculate the AST hash. If this is already around then we don't need to do very much!
        hash = ast_hash.calc_ast_hash(a)

        # Next, see if the hash file is there.
        query_file_path = os.path.join(cache_path, hash)
        cache_file = os.path.join(query_file_path, 'rep_cache.pickle')
        if os.path.isfile(cache_file):
            # We have a cache hit. Look it up.
            file = find_dataset(a)
            with open(cache_file, 'rb') as f:
                result_cache = pickle.load(f)
                return result_cache, extract_dataset_info(file)

        # Create the files to run in that location.
        if not os.path.exists(query_file_path):
            os.makedirs(query_file_path)

        src = generate_python_source(a)
        print(query_file_path)
        with open(os.path.join(query_file_path, 'transformer.py'), 'w') as python_file:
            python_file.write(src)

        os.system("ls -lht " + query_file_path)

        return GeneratedFileResult(hash, query_file_path)

    def get_generated_xAOD(self, a, cache_path: str):
        # Calculate the AST hash. If this is already around then we don't need to do very much!
        hash = ast_hash.calc_ast_hash(a)

        # Next, see if the hash file is there.
        query_file_path = os.path.join(cache_path, hash)
        cache_file = os.path.join(query_file_path, 'rep_cache.pickle')
        if os.path.isfile(cache_file):
            # We have a cache hit. Look it up.
            file = find_dataset(a)
            with open(cache_file, 'rb') as f:
                result_cache = pickle.load(f)
                return result_cache, extract_dataset_info(file)

        # Create the files to run in that location.
        if not os.path.exists(query_file_path):
            os.makedirs(query_file_path)

        exe = atlas_xaod_executor()
        f_spec = exe.write_cpp_files(exe.apply_ast_transformations(a), query_file_path)
        print(f_spec)

        os.system("ls -lht " + query_file_path)

        return GeneratedFileResult(hash, query_file_path)

    def translate_text_ast_to_zip(self, code: str) -> bytes:
        """Translate a text ast into a zip file as a memory stream

        Arguments:
            code            Text `qastle` version of the input ast generated by func_adl
            target_backend  Which backend to generate code for? xAOD or Uproot

        Returns
            bytes       Data that if written as a binary output would be a zip file.
        """

        if len(code) == 0:
            raise GenerateCodeException("Requested codegen for an empty string.")
        body = text_ast_to_python_ast(code).body
        if len(body) != 1:
            raise GenerateCodeException(
                f'Requested codegen for "{code}" yielded no code statements (or too many).')  # noqa: E501
        a = body[0].value

        # Generate the C++ code
        with TemporaryDirectory() as tempdir:
            if self.target_backend == 'xAOD':
                r = self.get_generated_xAOD(a, tempdir)
            else:
                r = self.get_generated_uproot(a, tempdir)

            # Zip up everything in the directory - we are going to ship it as back as part
            # of the message.
            z_filename = os.path.join(str(tempdir), f'joined.zip')
            zip_h = zipfile.ZipFile(z_filename, 'w', zipfile.ZIP_DEFLATED)
            self.zipdir(r.output_dir, zip_h)
            zip_h.close()

            with open(z_filename, 'rb') as b_in:
                return b_in.read()
