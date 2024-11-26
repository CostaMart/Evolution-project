from abc import ABC, abstractmethod
from typing import List
from annotated_types import T
from gliner import GLiNER
from pydantic import BaseModel
import spacy
from evaluate import load
from icecream import ic 
from knowledge_graph_maker import GraphMaker, Ontology, GroqClient
import json
from colorama import Fore, Style



"""grahp maker prompt:
"You are an expert at creating Knowledge Graphs. "
            "Consider the following ontology. \n"
            f"{self._ontology} \n"
            "The user will provide you with an input text delimited by ```. "
            "Extract all the entities and relationships from the user-provided text as per the given ontology. Do not use any previous knowledge about the context."
            "Remember there can be multiple direct (explicit) or implied relationships between the same pair of nodes. "
            "Be consistent with the given ontology. Use ONLY the labels and relationships mentioned in the ontology. "
            "describe the relationship like in the following example node_1 name of the relation node_2"
            "Format your output as a json with the following schema. \n"
            "[\n"
            "   {\n"
            '       node_1: Required, an entity object with attributes: {"label": "as per the ontology", "name": "Name of the entity"},\n'
            '       node_2: Required, an entity object with attributes: {"label": "as per the ontology", "name": "Name of the entity"},\n'
            "       relationship: Describe the relationship between node_1 and node_2 as per the context, in a few sentences.\n"
            "   },\n"
            "]\n"
            "Do not add any other comment before or after the json. Respond ONLY with a well formed json that can be directly read by a program."""


class Document(BaseModel):
  text: str
  metadata: dict


class LLMClient(ABC):
    @abstractmethod
    def __init__(self, model: str, temperature: float, top_p: float):
        pass

    @abstractmethod
    def generate(self, user_message: str, system_message: str) -> str:
        "Generate and return the result text as string"
        pass

class Evaluator:
    relationships = ["problem and possible cause"]
    labels = [  
              
                {"software": "any software component mentioned"},
                {"hardware": "any hardware component that doens't have any better specific label"},
                {"problems":"any problem in the system of which the sentence is talking about"},
                {"personal": "any human being involved into the system"}
            ]
       
    def __init__(self) -> None:
        self.model = GLiNER.from_pretrained("urchade/gliner_multi-v2.1")



    def evaluate_BERT_scores(self, prediction:str, references:str) -> dict:
        bertscore = load("bertscore")
        return bertscore.compute(predictions=[prediction], references=[references], lang= "en", device= "cuda:0", model_type = "microsoft/deberta-xlarge-mnli" )

      
    def evaluate_entity_sim(self, prediction:str, references:str, printEntities:bool= False)-> tuple[float, list[tuple], list[tuple]]:
        entities_prediction = self.model.predict_entities(prediction, self.labels + self.exact_match_labels, multi_label= False, threshold=0.5)
        entities_references = self.model.predict_entities(references, self.labels + self.exact_match_labels, multi_label= False, threshold=0.5)

        ic(entities_prediction)

      
        entities_prediction_filtered = [(entity["text"],entity["label"]) for entity in entities_prediction]
        entities_prediction_filtered = self.__list_remove_duplicate(entities_prediction_filtered)
        

        entities_reference_filtered = [(entity["text"], entity["label"]) for entity in entities_references]
        entities_reference_filtered = self.__list_remove_duplicate(entities_reference_filtered)
        ic(entities_reference_filtered)

        if printEntities:
            print(entities_prediction_filtered)
            print("--------------------------------------")
            print(entities_reference_filtered)
        
        return self.__entity_sim(entities_prediction_filtered,entities_reference_filtered), entities_prediction_filtered, entities_reference_filtered
    

    def evaluate_probmels_sim(self, prediction:str, references:str) -> float:
        entities_prediction = self.model.predict_entities(prediction, "problems", multi_label= False, threshold=0.4)
        entities_references = self.model.predict_entities(references, "problems", threshold=0.4)

        entities_prediction_filtered = [(entity["text"],entity["label"]) for entity in entities_prediction]
        entities_prediction_filtered = self.__list_remove_duplicate(entities_prediction_filtered)
        

        entities_reference_filtered = [(entity["text"], entity["label"]) for entity in entities_references]
        ic(entities_reference_filtered = self.__list_remove_duplicate(entities_reference_filtered))
        
        return self.__entity_sim(entities_prediction_filtered,entities_reference_filtered)
        
        
    
    def __entity_sim(self, predictions:List[str], references:List[str])-> float:
        nlp = spacy.load("en_core_web_md")
        matched_references = set()
        matches_total = set()


        for prediction in predictions:
            for word in references:
              
                if nlp(prediction[0]).similarity(nlp(word[0])) > 0.45: 
                    matched_references.add(prediction[0])
                    matches_total.add((prediction[0], word[0]))
            
        ic(matches_total)     


        return ic(len(matched_references))/ic(len(predictions)), ic(len(matched_references))/ic(len(references)) 


    def __list_remove_duplicate(self, listing:list[T])-> list[T]:
        s = set()
        for elem in listing:
            if elem[1] not in s:
                s.add(elem)
        return list(s)

    def compute_concept_coverage(self, prediction:str, reference:str, model_name:str = "llama-3.2-90b-vision-preview"):
        ontology = Ontology(
            labels= self.labels,
            relationships=self.relationships,
        )     
        groq = GroqClient(model = model_name, temperature=0, top_p= 1)
        return self.__relation_concept_coverage(prediction= prediction, reference= reference, ontology= ontology, llm_client= groq)
        
    
    def __relation_concept_coverage(self, prediction:str, reference:str, ontology:Ontology, llm_client:LLMClient)-> set[float, float]:
        system_prompt = """You are working as an evaluator. I will provide you with a set of nodes representing entities and their relationships. 
        For each pair evaluate if the relationship described in the 'relationship' field can be found in the given sentence, you can answer yes even if the relation is similar and not exactly the same. 
        Keep in mind then some entities might have slightly different names but still referring to the same entity.
        you MUST Only respond with one word: 'yes' or 'no' use the following format to respond:
        ["yes", "no"]
        The sentence will be separated from the rest by '##'."""
        
        graph_maker = GraphMaker(ontology=ontology, llm_client=llm_client)
        try:    
        
            # recall
            relations = graph_maker.from_text(reference)
            entities_recall = [entity.json() for entity in relations]
            results_josn = llm_client.generate(system_message=system_prompt, user_message=f"entites and relations: {entities_recall} ## sentence: {prediction}")
            result = ic(json.loads(results_josn))
            recall_numerator = [yes for yes in result if yes == "yes"]
            # end recall
      
        
            return len(recall_numerator)/len(entities_recall)
        
        except ZeroDivisionError:
            print(Fore.RED + f"0 relationships identified in one of the sentences" + Style.RESET_ALL)
       
            
    

if __name__== "__main__":
    CC = Evaluator().compute_concept_coverage("the cat on the table is instead a monkey that's why i cannot touch it, you have to know that im allergic to monkeys", 
    reference="The database of the service doesn't contain the right tables for the resources, so the service cannot retrieve them correctly causing the problem")
    ic(CC)
    