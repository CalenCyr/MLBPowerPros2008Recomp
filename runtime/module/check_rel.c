// SPDX-License-Identifier: GPL-3.0-or-later
#include "core/cpu.h"
#include "moderngekko/module.h"
#include <windows.h>
#include <bcrypt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef POWERPROS_EXPECTED_CHUNKS
#define POWERPROS_EXPECTED_CHUNKS 552
#endif
__declspec(dllimport) const StaticRecompModuleDesc* staticrecomp_get_module(void);
static unsigned fallbacks;
static void reject_fallback(CPUState* ctx,u32 raw,u32 pc) {
    (void)raw;(void)pc;++fallbacks;ctx->exception=1;
}
static int hash(const u8* bytes,u32 size,u8 out[32]) {
    BCRYPT_ALG_HANDLE algorithm=NULL;
    if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,NULL,0)<0) return 0;
    NTSTATUS status=BCryptHash(algorithm,NULL,0,(PUCHAR)bytes,size,out,32);
    BCryptCloseAlgorithmProvider(algorithm,0);return status>=0;
}
static int read_file(const char* path,u8* bytes,size_t size) {
    FILE* f=fopen(path,"rb");if(!f) return 0;
    int okay=fread(bytes,1,size,f)==size && fgetc(f)==EOF;fclose(f);return okay;
}
int main(int argc,char** argv) {
    enum { RAM_SIZE=24*1024*1024 };
    if(argc!=4) return 1;
    u8* original=(u8*)malloc(RAM_SIZE);u8* ram=(u8*)malloc(RAM_SIZE);
    if(!original||!ram||!read_file(argv[2],original,16*1024*1024)||!read_file(argv[3],original+16*1024*1024,8*1024*1024)) return 1;
    FILE* f=fopen(argv[1],"rb");if(!f) return 1;
    u8 magic[8],expected_hash[32],actual_hash[32];u32 count;
    if(fread(magic,1,8,f)!=8||memcmp(magic,"PPRELREF",8)||fread(expected_hash,1,32,f)!=32||fread(&count,4,1,f)!=1||!hash(original,RAM_SIZE,actual_hash)||memcmp(actual_hash,expected_hash,32)) return 1;
    const StaticRecompModuleDesc* module=staticrecomp_get_module();
    if(module->num_rel_modules!=1 || module->num_chunk_ranges!=POWERPROS_EXPECTED_CHUNKS || module->abi_version!=STATICRECOMP_ABI_VERSION || module->cpu_state_size!=sizeof(CPUState)) return 1;
    const ModernGekkoModuleRequirements requirements={GXRUNTIME_CPU_ABI_VERSION,sizeof(CPUState),"RL8E54"};
    ModernGekkoModuleStatus status=moderngekko_validate_module(module,&requirements);
    if(status!=MODERNGEKKO_MODULE_OK) {
        fprintf(stderr,"Frontend rejected combined module: %s\n",moderngekko_module_status_string(status));return 1;
    }
    {
        ModernGekkoModuleDesc invalid=*module;
        ModernGekkoRelModule rel=module->rel_modules[0];
        ModernGekkoRelSection sections[6];memcpy(sections,rel.sections,sizeof(sections));
        rel.sections=sections;invalid.rel_modules=&rel;sections[5].section_index=sections[0].section_index;
        if(moderngekko_validate_module(&invalid,&requirements)!=MODERNGEKKO_MODULE_INVALID_REL_MODULES) return 1;
    }
    for(u32 test=0;test<count;++test) {
        u32 entry,initial[32],expected[37];
        if(fread(&entry,4,1,f)!=1||fread(initial,4,32,f)!=32||fread(expected,4,37,f)!=37||fread(expected_hash,1,32,f)!=32) return 1;
        CPUState cpu;memset(&cpu,0,sizeof(cpu));memcpy(ram,original,RAM_SIZE);
        cpu.ram=ram;cpu.ram_size=RAM_SIZE;memcpy(cpu.gpr,initial,sizeof(initial));
        cpu.pc=entry;cpu.lr=0xDEADC0DCu;cpu.msr=0x2000u;cpu.instruction_fallback=reject_fallback;
        fallbacks=0;unsigned batches=0;
        while(cpu.pc!=0xDEADC0DCu&&!cpu.exception&&batches++<256) {
            cpu.downcount=1000000;
            if(!module->dispatch(&cpu,cpu.pc)) break;
        }
        u32 result[37];memcpy(result,cpu.gpr,sizeof(cpu.gpr));
        result[32]=cpu.cr;result[33]=cpu.xer;result[34]=cpu.ctr;result[35]=cpu.lr;result[36]=cpu.pc;
        if(cpu.exception||fallbacks||memcmp(result,expected,sizeof(result))||!hash(ram,RAM_SIZE,actual_hash)||memcmp(actual_hash,expected_hash,32)) {
            fprintf(stderr,"REL native mismatch case=%u entry=%08X pc=%08X fallback=%u exception=%u\n",test,entry,cpu.pc,fallbacks,cpu.exception);
            for(unsigned i=0;i<37;++i) if(result[i]!=expected[i]) fprintf(stderr,"register[%u] expected=%08X actual=%08X\n",i,expected[i],result[i]);
            return 1;
        }
    }
    if(fgetc(f)!=EOF) return 1;fclose(f);
    // A different BSS placement must never be dispatched with folded literals.
    CPUState guard;memset(&guard,0,sizeof(guard));memcpy(ram,original,RAM_SIZE);
    guard.ram=ram;guard.ram_size=RAM_SIZE;guard.pc=module->rel_modules[0].sections[0].linked_start;
    ram[0x575580+0x4C+6*8+3]^=4;
    if(module->dispatch(&guard,guard.pc)!=0) return 1;
    printf("PASS %u independent REL cases through combined module; zero instruction fallback; moved BSS rejected\n",count);
    free(ram);free(original);return 0;
}
