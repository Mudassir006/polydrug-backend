from typing import List, Dict

import requests
from SPARQLWrapper import SPARQLWrapper, JSON
from fastapi import HTTPException, FastAPI, Header, Depends
from jose import jwt
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

app = FastAPI(title="poly drug", debug=True)
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

KEYCLOAK_PUBLIC_KEY_URL = "http://localhost:8080/realms/polydrug"

cachedToken = ''
cachedUser = ''
cachedRole = ''

# Fuseki settings
FUSEKI_ENDPOINT = "http://localhost:3030/fastapi"
BASE_URI = "http://localhost/user/"
VOCAB = "http://localhost/vocab#"


def validate_token(authorization: str = Header(None)) -> dict:
    global cachedToken, cachedUser, cachedRole

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    token = authorization.replace("Bearer ", "")

    if token == cachedToken:
        print("Using cached user:", cachedUser)
        return {"user_id": cachedUser, "user_role": cachedRole}
    else:
        print("Fetching new token information")
        response = requests.get(KEYCLOAK_PUBLIC_KEY_URL)
        public_keys = response.json()["public_key"]

        try:
            decoded_token = jwt.decode(
                token,
                '-----BEGIN PUBLIC KEY-----\n' + public_keys + '\n-----END PUBLIC KEY-----',
                algorithms=["RS256"],
                options={'exp': False, 'verify_signature': False, 'verify_aud': False,'verify-exp':False}
            )
            print(f'Decoded token: {decoded_token}')

            cachedToken = token

            return {"user_id": cachedUser, "user_role": cachedRole}

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")


def fetch_compounds_from_fuseki(selected_compounds, selected_properties):
    sparql = SPARQLWrapper(FUSEKI_ENDPOINT)
    sparql.setReturnFormat(JSON)

    select_part = """SELECT ?PolymerName ?ChainLength ?ChainNumber ?ForceField ?AC3 ?AC4 ?AC5 ?AC6 ?AC8 ?AC9 ?AC10 ?AC11 ?E1S11 
        ?E1S12 ?E1S14 ?E1S15 ?E1S21 ?E1S22 ?E1S24 ?E1S25 ?E21 ?E22 ?E23 ?E24 ?E25 ?E27 ?E28 ?E31 ?E32 ?E33 ?E34 ?E35 
        ?E37 ?E38 ?E41 ?E42 ?E44 ?E45 ?E46 ?E5S11 ?E5S12 ?E5S14 ?E5S15 ?E5S16 ?E5S21 ?E5S22 ?E5S24 ?E5S25 ?E5S26 
        ?E5S31 ?E5S32 ?E5S34 ?E5S35 ?E5S36 ?SA11 ?SA12 ?SA14 ?SA15 ?SA21 ?SA22 ?SA24 ?SA25 """
    for prop in selected_properties:
        select_part += f"?{prop.value}"

    query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX polymer: <https://polytarget.cms.uni-jena.de/polymer/>
        PREFIX pmdco: <https://material-digital.de/pmdco/>
        PREFIX wb: <http://wikiba.se/ontology#>
        
        
        """ + select_part + """

        
          
          
          
           
           
           WHERE {
            ?MDprocessAll a polymer:MolecularDynamicsSimulationProcess;
            pmdco:hasInitialProcess ?iniProcess;
            pmdco:hasFinalProcess ?FinalProcess.

            ?iniProcess polymer:hasPolymerName ?PolymerName;
            polymer:isCellOptimization ?AC5; 
            polymer:isCheckCloseContact ?AC6; 
            polymer:hasForceField ?ForceField; 
            polymer:hasCalculationQuality ?AC8; 
            polymer:hasPolymerConfigurationNumber ?AC10; 
            polymer:hasLowestEnergyFrameNumber ?AC11. 
        
        

    """

    # Add the selected compounds to the query
    query += "VALUES ?PolymerName { " + " ".join(f"'{compound}'" for compound in selected_compounds) + " }"

    # Add the rest of the query
    query += """
        

            ?iniProcess polymer:hasPolymer/polymer:hasMaterialProperty
        [a polymer:PolymerChainLength; #AC1
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?ChainLength],
        [a polymer:PolymerChainNumber; #AC2
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?ChainNumber],
        [a polymer:InitialDensity; #AC3
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?AC3],  
        [a polymer:RampDensityRatio; #AC4
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?AC4],
    
    # AmorphousCellLoadingTime should be metadata #TODO
        [a polymer:AmorphousCellLoadingTime; #AC9
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?AC9].   
    
# Equilibration1-1
?iniProcess pmdco:hasNextProcess ?EquiProcess_1_1.
?EquiProcess_1_1 polymer:hasEnsemble ?E1S11; #E1S11
polymer:hasCalculationQuality ?E1S15; #E1S15
polymer:hasPolymer/polymer:hasMaterialProperty
[a polymer:NVTDuration; #E1S14
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E1S14],
        [a polymer:Temperature; #E1S12
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E1S12].

# Equilibration1-2
?EquiProcess_1_1 pmdco:hasNextProcess ?EquiProcess_1_2.
?EquiProcess_1_2 polymer:hasEnsemble ?E1S21; #E1S21  
polymer:hasCalculationQuality ?E1S25; #E1S25
polymer:hasPolymer/polymer:hasMaterialProperty
[a polymer:NVTDuration; #E1S24
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E1S24],
        [a polymer:Temperature; #E1S22
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E1S22].

# Equilibration2
?EquiProcess_1_2 pmdco:hasNextProcess ?EquiProcess_2.
?EquiProcess_2 polymer:hasEnsemble ?E21; #E21
polymer:hasAnnealingStepNumber ?E24; #E24
polymer:hasThermostat ?E27; #E27
polymer:hasCalculationQuality ?E28; #E28
polymer:hasPolymer/polymer:hasMaterialProperty
        [a polymer:StartTemperature; #E22
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E22],
        [a polymer:EndTemperature; #E23
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E23],
        [a polymer:AnnealingDuration; #E25
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E25].    

# Equilibration3
?EquiProcess_2 pmdco:hasNextProcess ?EquiProcess_3.
?EquiProcess_3 polymer:hasEnsemble ?E31; #E31
polymer:hasAnnealingStepNumber ?E34; #E34
polymer:hasThermostat ?E37; #E37
polymer:hasCalculationQuality ?E38; #E38
polymer:hasPolymer/polymer:hasMaterialProperty
        [a polymer:StartTemperature; #E32
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E32],
        [a polymer:EndTemperature; #E33
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E33],
        [a polymer:AnnealingDuration; #E35
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E35].

# Equilibration4
?EquiProcess_3 pmdco:hasNextProcess ?EquiProcess_4.
?EquiProcess_4 polymer:hasEnsemble ?E41; #E41
polymer:hasCalculationQuality ?E45; #E45
polymer:hasAnnealingLowestEnergyFrameNumber ?E46; #E46
polymer:hasPolymer/polymer:hasMaterialProperty
        [a polymer:Temperature; #E42
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E42],
        [a polymer:NVTDuration; #E44
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E44].

# Equilibration5-1
?EquiProcess_4 pmdco:hasNextProcess ?EquiProcess_5_1.
?EquiProcess_5_1 polymer:hasEnsemble ?E5S11; #E5S11
polymer:hasBarostat ?E5S14; #E5S14                 
polymer:hasCalculationQuality ?E5S16; #E5S16
polymer:hasPolymer/polymer:hasMaterialProperty
        [a polymer:Temperature; #E5S12
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E5S12],
        [a polymer:NPTDuration; #E5S15
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E5S15].

# Equilibration5-2
?EquiProcess_5_1 pmdco:hasNextProcess ?EquiProcess_5_2.
?EquiProcess_5_2 polymer:hasEnsemble ?E5S21; #E5S21
polymer:hasBarostat ?E5S24; #E5S24                 
polymer:hasCalculationQuality ?E5S26; #E5S26
polymer:hasPolymer/polymer:hasMaterialProperty
        [a polymer:Temperature; #E5S22
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E5S22],
        [a polymer:NPTDuration; #E5S25
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E5S25].
  
# Equilibration5-3
?EquiProcess_5_2 pmdco:hasNextProcess ?EquiProcess_5_3.
?EquiProcess_5_3 polymer:hasEnsemble ?E5S31; #E5S31
polymer:hasBarostat ?E5S34; #E5S34                 
polymer:hasCalculationQuality ?E5S36; #E5S36
polymer:hasPolymer/polymer:hasMaterialProperty
        [a polymer:Temperature; #E5S32
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E5S32],
        [a polymer:NPTDuration; #E5S35
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?E5S35].

# Sampling1-1
?EquiProcess_5_3 pmdco:hasNextProcess ?SamplingProcess_1_1.
?SamplingProcess_1_1 polymer:hasEnsemble ?SA11; #SA11               
polymer:hasCalculationQuality ?SA15; #SA15
polymer:hasPolymer/polymer:hasMaterialProperty
        [a polymer:Temperature; #SA12
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?SA12],
        [a polymer:SamplingDuration; #SA14
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?SA14].
  
# Sampling1-2
?SamplingProcess_1_1 pmdco:hasNextProcess ?SamplingProcess_1_2.
?SamplingProcess_1_2 polymer:hasEnsemble ?SA21; #SA21               
polymer:hasCalculationQuality ?SA25; #SA25
polymer:hasPolymer/polymer:hasMaterialProperty
        [a polymer:Temperature; #SA22
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?SA22],
        [a polymer:SamplingDuration; #SA24
           polymer:hasMaterialPropertyValue/wb:quantityAmount ?SA24]. 
        

        # Selected properties to query
        ?FinalProcess polymer:hasPolymer/polymer:hasMaterialProperty
    """

    # Add the selected properties to the query
    for prop in selected_properties:
        query += f"[a polymer:{prop.value}; polymer:hasMaterialPropertyValue/wb:quantityAmount ?{prop.value}],"

    query = query.rstrip(",") + "."

    query += """}"""

    # print(query)

    sparql.setQuery(query)

    try:
        results = sparql.query().convert()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return results.get('results', {}).get('bindings', [])


selected_compounds = ['Pentane', 'Butane']
selected_properties = [{
    "value": "CohesiveEnergyDensity",
}]

# print(fetch_compounds_from_fuseki(selected_compounds, selected_properties))


class Properties(BaseModel):
    value: str


@app.post("/compounds", response_model=List[Dict], )
def get_compounds(selected_compounds: List[str], selected_properties: List[Properties],
                  # token: str = Depends(validate_token)
                  ):
    return fetch_compounds_from_fuseki(selected_compounds, selected_properties)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

#
