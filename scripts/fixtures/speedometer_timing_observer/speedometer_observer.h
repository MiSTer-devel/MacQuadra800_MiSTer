#ifndef SPEEDOMETER_OBSERVER_H
#define SPEEDOMETER_OBSERVER_H
#include <array>
#include <cstdint>
#include <iomanip>
#include <ostream>
#include <string>

// Host-side observer only. Input memory transfers are successful, CE-qualified
// core-side acknowledgements, sampled BEFORE the edge. Addresses are logical;
// data has already traversed the real MMU/cache. Never dereferences guest RAM.
namespace speedometer {
struct Context {
    std::array<uint32_t,7> mmu{}; // TC,URP,SRP,ITT0,ITT1,DTT0,DTT1
    bool operator==(const Context& b) const { return mmu==b.mmu; }
};
struct Registers {
    std::array<uint32_t,8> d{},a{};
    uint16_t sr=0;
    bool pending=false,aux=false;
    uint8_t pending_reg=0;
    uint32_t pending_data=0;
};
struct Bus {
    uint64_t cycle=0;
    uint32_t pc=0,addr=0,data=0;
    uint8_t bytes=0,fc=0;
    bool request=false,ack=false,error=false,ce=true,instruction=false,write=false;
};
inline void apply_pending(Registers& r,bool we,uint8_t reg,uint32_t data,
                          bool aux,uint8_t aux_sel,uint32_t aux_data) {
    r.pending=we;r.pending_reg=reg;r.pending_data=data;r.aux=aux;
    if(we) {if(reg<8)r.d[reg]=data;else r.a[reg-8]=data;}
    const unsigned sp=!(r.sr&0x2000)?0:((r.sr&0x1000)?2:1);
    if(aux && aux_sel==sp)r.a[7]=aux_data;
}

class Observer {
    struct Byte { uint32_t addr=0; uint8_t fc=0,value=0; bool valid=false; };
    // Direct-mapped bounded cache; collisions only prevent identification.
    std::array<Byte,4096> code_{};
    Context context_{};
    bool context_valid_=false,identified_=false,reset_=false;
    uint32_t base_=0,a5_=0,a6_=0;
    uint8_t code_fc_=0;
    unsigned test_=0;
    uint64_t limit_,records_=0,identities_=0,starts_=0,stops_=0,contexts_=0;
    unsigned prefix_=0,prefix_test_=0;
    uint32_t prefix_pc_=0,prefix_a5_=0;
    std::ostream& out_;
    bool have_start_=false,have_stop_=false,have_aggregate_=false,micro_start_=false,window_=false;
    uint64_t start_=0,stop_=0,start_cycle_=0,stop_cycle_=0;
    uint32_t before_d4_=0,elapsed_=0;
    uint8_t elapsed_mask_=0;

    bool emit(const char* type,uint64_t cycle) {
        if(records_>=limit_) return false;
        ++records_;
        out_ << type << " cycle=" << cycle;
        return true;
    }
    void hex(const char* key,uint32_t v) { out_<<' '<<key<<"=0x"<<std::hex<<v<<std::dec; }
    const char* name() const { return test_==0?"Queens":"Sieve"; }
    static unsigned slot(uint32_t addr,uint8_t fc) { return (addr^(uint32_t(fc)<<8))&4095; }
    void put(uint32_t addr,uint8_t fc,uint8_t v) { code_[slot(addr,fc)]={addr,fc,v,true}; }
    bool get(uint32_t addr,uint8_t fc,uint8_t& v) const {
        const auto& b=code_[slot(addr,fc)];
        if(!b.valid || b.addr!=addr || b.fc!=fc) return false;
        v=b.value; return true;
    }
    bool word(uint32_t addr,uint8_t fc,uint16_t& v) const {
        uint8_t hi,lo;
        if(!get(addr,fc,hi)||!get(addr+1,fc,lo)) return false;
        v=uint16_t((hi<<8)|lo); return true;
    }
    bool signature(uint32_t pc,uint8_t fc,unsigned test) const {
        // Unique immutable non-relocated instruction/extension bytes. The
        // following JSR's relocated absolute address is intentionally omitted.
        const uint8_t s[]={0x3b,0x7c,0,4,0xbe,0xaa,0x3b,0x7c,0,
                           uint8_t(test?0xe2:0x92),0xbe,0xac};
        for(unsigned i=0;i<12;i++) { uint8_t b; if(!get(pc-12+i,fc,b)||b!=s[i]) return false; }
        return true;
    }
    void snapshot(const char* type,uint64_t cycle,uint32_t pc,uint16_t ir,const Registers& r) {
        if(!emit(type,cycle)) return;
        out_<<" test="<<name(); hex("pc",pc); hex("ir",ir); hex("base",base_); hex("sr",r.sr);
        for(unsigned i=0;i<8;i++) { std::string k="d"+std::to_string(i); hex(k.c_str(),r.d[i]); }
        for(unsigned i=0;i<8;i++) { std::string k="a"+std::to_string(i); hex(k.c_str(),r.a[i]); }
        out_<<" rf_pending="<<r.pending<<" aux_pending="<<r.aux;
        hex("pending_reg",r.pending_reg); hex("pending_data",r.pending_data);
        out_<<'\n';
    }
public:
    explicit Observer(std::ostream& out,uint64_t limit=512):limit_(limit),out_(out) {
        out_<<"META format=speedometer-observer-v1 clock_unit=33MHz_rising_edges limit="<<limit
            <<" resource_sha256=af67113bceb4eb906e973a9b747a0b1925b9d64c62f0f9a84bc6f0578839ca80\n";
    }
    bool bounded() const { return records_>=limit_; }
    uint64_t identities() const { return identities_; }
    void invalidate(uint64_t cycle,const char* reason) {
        if(identified_ && emit("INVALIDATE",cycle))out_<<" reason="<<reason<<'\n';
        code_={};identified_=false;prefix_=0;
        have_start_=have_stop_=have_aggregate_=window_=false;
    }
    void reset(bool value) {
        if(value && !reset_) { context_valid_=false; identified_=false; code_={};prefix_=0;
            have_start_=have_stop_=have_aggregate_=window_=false; }
        reset_=value;
    }
    void context(const Context& c,uint64_t cycle) {
        if(!context_valid_ || !(context_==c)) {
            ++contexts_;invalidate(cycle,"MMU_REGISTERS");context_=c;context_valid_=true;
        }
    }
    void bus(const Bus& b) {
        if(reset_ || bounded() || !b.ce || !b.request || !b.ack || b.error ||
           (b.bytes!=1 && b.bytes!=2 && b.bytes!=4)) return;
        if(b.instruction && !b.write) {
            for(unsigned i=0;i<b.bytes;i++) put(b.addr+i,b.fc,uint8_t(b.data>>(8*(b.bytes-1-i))));
            return;
        }
        if(b.write) {
            // Fresh EXECUTED prefix proof, not merely stale fetched bytes:
            // both MOVE.W instructions must actually write their known
            // immediate values at the known A5-relative logical addresses.
            if(prefix_==1 && b.pc==prefix_pc_ && b.addr==prefix_a5_-0x4156 && b.bytes==2 && uint16_t(b.data)==4)
                prefix_=2;
            else if(prefix_==3 && b.pc==prefix_pc_+6 && b.addr==prefix_a5_-0x4154 && b.bytes==2 &&
                    (uint16_t(b.data)==0x92 || uint16_t(b.data)==0xe2)) {
                prefix_test_=uint16_t(b.data)==0xe2;prefix_=4;
            }
            // Any logical write to a captured instruction invalidates it;
            // aliases may invalidate conservatively only when later fetched.
            for(unsigned i=0;i<b.bytes;i++) for(uint8_t fc: {uint8_t(2),uint8_t(6)}) {
                auto& x=code_[slot(b.addr+i,fc)];
                if(x.valid && x.addr==b.addr+i && x.fc==fc) x.valid=false;
            }
        }
        if(!identified_ || !window_) return;
        const uint32_t selector=a5_-0x36f2, taskptr=a5_-0x205c, taskcount=a5_-0x6dfa;
        bool watched=false;
        for(unsigned i=0;i<b.bytes;i++) {
            const uint32_t addr=b.addr+i;
            watched|=addr==selector || uint32_t(addr-(a6_-16))<16 ||
                     uint32_t(addr-taskptr)<4 || uint32_t(addr-taskcount)<4;
            // Only the actual ADD.L -4(A6),D4 operand read supplies the
            // authoritative elapsed value; never infer it from backing RAM.
            const uint32_t aggregate=base_+(0x657a1-0x62561)+(test_?0x494:0);
            if(!b.write && b.pc==aggregate && uint32_t(addr-(a6_-4))<4) {
                const unsigned shift=8*(3-(addr-(a6_-4)));
                const uint32_t byte=(b.data>>(8*(b.bytes-1-i)))&255;
                elapsed_=(elapsed_&~(255u<<shift))|(byte<<shift);
                elapsed_mask_|=uint8_t(1u<<(addr-(a6_-4)));
            }
        }
        if(watched && emit("MEM",b.cycle)) {
            out_<<" test="<<name()<<" write="<<b.write<<" bytes="<<unsigned(b.bytes)<<" fc="<<unsigned(b.fc);
            hex("pc",b.pc);hex("logical",b.addr);hex("value",b.data);out_<<'\n';
        }
    }
    void dispatch(uint64_t cycle,uint32_t pc,uint16_t ir,const Registers& r) {
        if(reset_ || bounded()) return;
        const uint8_t fc=(r.sr&0x2000)?6:2;
        const bool live_prefix=prefix_==4 && pc==prefix_pc_+12 && r.a[5]==prefix_a5_;
        const unsigned live_test=prefix_test_;
        if(ir==0x3b7c) {
            if(prefix_==2 && pc==prefix_pc_+6 && r.a[5]==prefix_a5_)prefix_=3;
            else {prefix_=1;prefix_pc_=pc;prefix_a5_=r.a[5];}
        } else prefix_=0;
        if(ir==0x4eb9 && live_prefix) for(unsigned t=0;t<2;t++) if(t==live_test && signature(pc,fc,t)) {
            test_=t; code_fc_=fc;
            base_=pc-((t?0x65bb1:0x65729)-0x62561);
            a5_=r.a[5];a6_=r.a[6]; identified_=true;++identities_;
            have_start_=have_stop_=have_aggregate_=window_=false;
            snapshot("IDENTIFY",cycle,pc,ir,r);
            if(emit("IDENTITY_CONTEXT",cycle)) {
                for(unsigned i=0;i<7;i++) {std::string k="mmu"+std::to_string(i);hex(k.c_str(),context_.mmu[i]);}
                out_<<" live_prefix_writes=2\n";
            }
        }
        if(!identified_) return;
        if((ir==0xa058 || ir==0xa059 || ir==0xa05a) && window_)
            snapshot("TIME_MANAGER_TRAP",cycle,pc,ir,r);
        if(fc!=code_fc_) return;
        const uint32_t offset=pc-base_-(test_?0x494:0);
        struct Point {uint32_t file;uint16_t opcode;const char* event;};
        const Point points[]={
          {0x65747,0x4a2d,"SELECT_START"},{0x65751,0xa193,"MICRO_START_CALL"},
          {0x65753,0x225f,"MICRO_START_RETURN"},{0x6575b,0x4eb9,"FALLBACK_START_CALL"},
          {0x65761,0x4eb9,"FALLBACK_PRIME_CALL"},{0x6576b,0x4eb9,"KERNEL_CALL"},
          {0x65771,0x4a2d,"KERNEL_RETURN"},{0x6577d,0xa193,"MICRO_STOP_CALL"},
          {0x6577f,0x225f,"MICRO_STOP_RETURN"},{0x6578d,0x4eb9,"SUBTRACT_CALL"},
          {0x65793,0x504f,"SUBTRACT_RETURN"},{0x65797,0x4eb9,"FALLBACK_STOP_CALL"},
          {0x6579d,0x2d40,"FALLBACK_STOP_RETURN"},{0x657a1,0xd8ae,"AGGREGATE_BEFORE"},
          {0x657a5,0x5285,"AGGREGATE_AFTER"},{0x657a7,0x594f,"COUNT_AFTER"},
          {0x657a9,0xa975,"TICK_CALL"},{0x657ab,0x201f,"TICK_RETURN_STACK"},
          {0x657ad,0xb08a,"TICK_COMPARE"},{0x657af,0x6590,"TICK_BRANCH"}};
        for(const auto& p:points) if(offset==p.file-0x62561) {
            if(ir!=p.opcode) {
                snapshot("IDENTITY_LOST",cycle,pc,ir,r);identified_=false;return;
            }
            a5_=r.a[5];a6_=r.a[6];
            if(p.file==0x65747) window_=true;
            if(p.file==0x6576b) {
                uint16_t op,selector;
                if(!word(pc-4,fc,op)||!word(pc-2,fc,selector)||op!=0x3f3c||selector!=(test_?12:6)) {
                    snapshot("KERNEL_SELECTOR_UNVERIFIED",cycle,pc,ir,r);
                    identified_=false;return;
                }
            }
            snapshot(p.event,cycle,pc,ir,r);
            if(p.file==0x65753) {
                start_=(uint64_t(r.a[0])<<32)|r.d[0];start_cycle_=cycle;
                have_start_=true;micro_start_=true;have_stop_=false;++starts_;
            }
            if(p.file==0x6575b) { have_start_=true;micro_start_=false;have_stop_=false;start_cycle_=cycle; }
            if(p.file==0x6577f) {
                stop_=(uint64_t(r.a[0])<<32)|r.d[0];stop_cycle_=cycle;have_stop_=true;++stops_;
                if(have_start_ && micro_start_ && emit("RAW_DELTA",cycle)) {
                    out_<<" test="<<name()<<" start="<<start_<<" stop="<<stop_
                        <<" delta_u64="<<(stop_-start_)<<" backwards="<<(stop_<start_)
                        <<" observed_cycles="<<(stop_cycle_-start_cycle_)<<'\n';
                }
            }
            if(p.file==0x657a1) {before_d4_=r.d[4];have_aggregate_=true;elapsed_=0;elapsed_mask_=0;}
            if(p.file==0x657a5 && have_aggregate_ && emit("AGGREGATE_CHECK",cycle)) {
                out_<<" test="<<name()<<" elapsed_read_valid="<<(elapsed_mask_==15);
                hex("guest_elapsed",elapsed_);hex("d4_before",before_d4_);hex("d4_after",r.d[4]);
                out_<<" sum_matches="<<(elapsed_mask_==15 && r.d[4]==uint32_t(before_d4_+elapsed_));
                if(have_start_&&micro_start_&&have_stop_)out_<<" raw_low32_matches="<<(elapsed_mask_==15&&elapsed_==uint32_t(stop_-start_));
                out_<<'\n';
            }
            if(p.file==0x657af) {
                window_=false;
                // BCS repeats this exact bracket only while C=1. Once the
                // test falls through, require a newly executed setup prefix.
                if(!(r.sr&1))identified_=false;
            }
            return;
        }
    }
    void summary() {
        out_<<"SUMMARY records="<<records_<<" identities="<<identities_<<" micro_starts="<<starts_
            <<" micro_stops="<<stops_<<" contexts="<<contexts_<<" capped="<<bounded()<<'\n';out_.flush();
    }
};
}
#endif
