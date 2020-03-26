[![GitHub Actions Status](https://github.com/ssl-hep/ServiceX_Code_Generator_FuncADL_xAOD/workflows/CI/CD/badge.svg)](https://github.com/ssl-hep/ServiceX_Code_Generator_FuncADL_xAOD/actions)
[![Code Coverage](https://codecov.io/gh/ssl-hep/ServiceX_Code_Generator_FuncADL_xAOD/graph/badge.svg)](https://codecov.io/gh/ssl-hep/ServiceX_Code_Generator_FuncADL_xAOD)


ServiceX Code Generator
-----------------------
This microservice is a REST API that will generate C++ source code that runs in 
the ATLAS environment to generate code that will extract columns of data from 
ATLAS xAOD binary files. The query to extract the data is generated by the 
func-adl LINQ-like language, and specified to the service using the ast-language.

Usage
-----
This repo builds a container to be used in the `ServiceX` application. You can 
see the containers on docker hub.

### Running the web service

The default is to run a web service that will take a `qastle` as input and 
return a binary zip file as output. To start that up, use the following 
docker command:

```
 docker run -it --rm -p 5000:5000  sslhep/servicex_code_gen_func_adl_xaod:latest sslhep
```

You can now make queries against port 5000.

### Translating a `qastle` into code
For debugging purposes you sometimes want to translate an `ast` into a zip file. 
This container will also do that for you:

```
AST="(call ResultTTree (call Select (call SelectMany (call EventDataset (list 'localds://did_01')) (lambda (list e) (call (attr e 'Jets') ''))) (lambda (list j) (call (attr j 'pt')))) (list 'jet_pt') 'analysis' 'junk.root')" 
echo $AST | docker run -i --rm -v ${PWD}:/zip sslhep/servicex_code_gen_func_adl_xaod:master from_ast_to_zip.py -z /zip/junk.zip
```

After running, that will leave a `zip` file in your home directory that contains 
the 6 or so files necessary to run the requested transform. The only thing 
missing are the input files.



Development
-----------
- Note that this service requires Python 3.7 or above
- Use `pytest` to run the tests
- Use the `postman` template to send some sample queries to the service.

- Create a bash shell in the container with the source code mounted in /code
and an Docker volume provided to store the generated code.

```
docker run --rm -it \
  --mount type=bind,source=$(pwd),target=/code \
  --mount type=bind,source=$(pwd)/generated,target=/generated \
  --entrypoint bash \
  sslhep/servicex_code_gen_funcadl_xaod:develop 
```

Then cd to /code and run the script as
```bash
 echo $AST | PYTHONPATH=/code python scripts/from_ast_to_zip.py -z /generated/foo.zip --uproot
```


