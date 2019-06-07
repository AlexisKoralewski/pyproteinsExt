import pyproteinsExt.hmmrContainerFactory as hmmr 
import pyproteinsExt.tmhmmContainerFactory as tmhmm
import pyproteinsExt.fastaContainerFactory as fasta
import pyproteinsExt.proteinContainer

def check_if_same_proteins(dic_container):
    hmmr_proteins=set()
    tmhmm_proteins=set()
    fasta_proteins=set()
    if dic_container['hmmr']:
        hmmr_proteins=set([p for p in dic_container['hmmr'].pIndex])
    if dic_container['tmhmm']:    
        tmhmm_proteins=set([e.prot for e in dic_container['tmhmm']])
    if dic_container['fasta']:
        fasta_proteins=set([e.prot for e in dic_container['fasta']])

    list_proteins=[hmmr_proteins,tmhmm_proteins,fasta_proteins]
    if len(list_proteins)<=1: 
        return True
    for i in range(len(list_proteins)):
        for j in range(i+1,len(list_proteins)): 
            prot1=list_proteins[i]
            prot2=list_proteins[j]
            if len(prot1)!=len(prot2):
                return False
            if prot1.difference(prot2):
                return False
    return True            


def parse(hmmrOut,tmhmmOut,fastaOut):
    container=TopologyContainer()
    hmmrContainer=hmmr.parse(hmmrOut)
    tmhmmContainer=tmhmm.parse(tmhmmOut)
    fastaContainer=fasta.parse(fastaOut)   

    #if len(fastaContainer)==0: 
    #    return container 

    dic_container={'hmmr':hmmrContainer,'tmhmm':tmhmmContainer,'fasta':fastaContainer}
    if not check_if_same_proteins(dic_container):
        raise Exception("not same proteins ",hmmrOut,tmhmmOut,"Check !")
    container.addParsing(TopologyContainer(input=dic_container))   
    return container

class TopologyContainer(pyproteinsExt.proteinContainer.Container):
    def __init__(self, input=None):
        super().__init__(_parseBuffer,input)  

    def filter(self,fPredicat,**kwargs): 
        new_container=TopologyContainer()
        for e in self : 
            if fPredicat(e,**kwargs):
                new_container.addEntry(e)
        return new_container

    def get_domain_mfasta(self,domain,evalue):
        mfasta=''
        for e in self: 
            for match in e.hmmr: 
                for hit in match.data:
                    if hit.hmmID == domain and float(hit.iEvalue)<=evalue:
                        header=">"+hit.aliID+" "+hit.hmmID
                        #print(header)
                        seq=self.get_seq(hit)
                        mfasta+=header+"\n"+seq+"\n"
        return mfasta                

    def get_seq(self,hit):
        seq=hit.aliStringLetters   
        seq=seq.replace("-","")
        seq=seq.upper()
        return seq    

    def proteins_mfasta(self):
        mfasta=''
        for e in self: 
            mfasta+=">"+e.fasta.header+"\n"+e.fasta.seq+"\n"
        return mfasta    

    def complete_hmmr(self,hmmscan_out):  
        container=hmmr.parse(hmmscan_out)
        new_proteins=set([h.prot for h in container.hmmrEntries])
        self_proteins=set(self.entries.keys())
        if len(new_proteins)!=len(self_proteins):
            raise Exception("full Pfam proteins and original proteins are not the same")
        else: 
            if new_proteins.difference(self_proteins):
                raise Exception("full Pfam proteins and original proteins are not the same")        
        for e in self: 
            hits=[h for h in container.hmmrEntries if h.prot==e.prot]
            e.hmmr+=hits

    def filter_hit(self,fPredicat,**kwargs):
        new_container=TopologyContainer()
        for e in self: 
            add=False
            hit_to_add=[]
            for hit in e.hmmr: 
                if fPredicat(hit,**kwargs):
                    add=True
                    hit_to_add.append(hit)
            if add :     
                new_e=Topology(e.prot,hit_to_add,e.tmhmm,e.fasta,e.taxo)    
                new_container.addEntry(new_e)
        return new_container 
    def compute_overlapped_domains(self,overlap_accept_size):
        self.reinitialize_overlapped_domains()
        for e in self: 
            for i in range(len(e.hmmr)):
                for j in range(i+1,len(e.hmmr)):
                    hit1=e.hmmr[i]
                    hit2=e.hmmr[j]
                    if hit1.is_overlapping(hit2,overlap_accept_size):
                        hit1.overlapped_hits.append(hit2)
                        hit2.overlapped_hits.append(hit1)
class Topology(): 
    def __init__(self,prot,hmmr,tmhmm,fasta,taxo=None):
        self.prot=prot
        self.hmmr=hmmr
        self.tmhmm=tmhmm
        self.fasta=fasta
        self.taxo=taxo

    def get_taxo(self,function_get_taxid):
        ncbi=NCBITaxa()
        taxname=None
        taxrank=None
        taxid=function_get_taxid(self)
        taxname_dic=ncbi.get_taxid_translator([taxid])
        if taxname_dic:
            taxname=taxname_dic[int(taxid)]
            taxrank_dic=ncbi.get_rank([taxid])
            if taxrank_dic : 
                taxrank=taxrank_dic[int(taxid)]
        self.taxo=Taxo(taxid,taxname,taxrank)  

def _parseBuffer(dic_container):
    hmmrContainer=dic_container['hmmr']
    tmhmmContainer=dic_container['tmhmm']
    fastaContainer=dic_container['fasta']
    dic_obj={}
    for p in hmmrContainer.pIndex: 
        hmmr=hmmrContainer.pIndex[p]
        tmhmm=tmhmmContainer.entries[p]
        fasta=fastaContainer.entries[p]
        obj=Topology(p,hmmrContainer.pIndex[p],tmhmm,fasta)
        dic_obj[p]=obj
    return dic_obj                   

class Taxo():
    def __init__(self,taxid,taxname,taxrank):
        self.taxid=taxid
        self.taxname=taxname
        self.taxrank=taxrank
