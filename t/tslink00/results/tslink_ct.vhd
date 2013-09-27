library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library ftl;
use ftl.ftlbase.all;

package comp_tslink_ct is
component tslink_ct is
port (
    clk : in  std_ulogic;
    rst : in  std_ulogic;
    LinkIn : in std_ulogic;
    IValid : in std_ulogic;
    QAck : in std_ulogic;
    IData : in std_logic_vector(7 downto 0);
    IAck : out std_ulogic;
    ShiftEnable : out std_ulogic;
    LinkOut : out std_ulogic;
    QValid : out std_ulogic
);
end component;
end package;


library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library ftl;
use ftl.ftlbase.all;

entity tslink_ct is
port (
    clk : in  std_ulogic;
    rst : in  std_ulogic;
    LinkIn : in std_ulogic;
    IValid : in std_ulogic;
    QAck : in std_ulogic;
    IData : in std_logic_vector(7 downto 0);
    IAck : out std_ulogic;
    ShiftEnable : out std_ulogic;
    LinkOut : out std_ulogic;
    QValid : out std_ulogic
);
end entity;

architecture rtl of tslink_ct is
-- Undefined attributes (assuming inputs):
signal S_QAck : std_ulogic;
signal S_IData : std_logic_vector(7 downto 0);
signal S_IValid : std_ulogic;
signal S_LinkIn : std_ulogic;

-- Defined attributes:
signal FS10 : std_ulogic;
signal FP11 : std_ulogic;
signal FP21 : std_ulogic;
signal FP111 : std_ulogic;
signal FP151 : std_ulogic;
signal FP161 : std_ulogic;
signal FS40 : std_ulogic;
signal FP171 : std_ulogic;
signal FP281 : std_ulogic;
signal FS2_cnd0 : std_ulogic;
signal FS2_cnd1 : std_ulogic;
signal FS22 : std_ulogic;
signal FS3_cnd0 : std_ulogic;
signal FS3_cnd1 : std_ulogic;
signal FT9F2 : std_ulogic;
signal FP2S_C01 : std_ulogic;
signal FP2S_C11 : std_ulogic;
signal FP2S_C21 : std_ulogic;
signal FP2S_C31 : std_ulogic;
signal FP2S_C41 : std_ulogic;
signal FP2S_C51 : std_ulogic;
signal FP2S_C61 : std_ulogic;
signal FP2S_C71 : std_ulogic;
signal FP2S_C81 : std_ulogic;
signal FS2P_C01 : std_ulogic;
signal FS2P_C11 : std_ulogic;
signal FS2P_C21 : std_ulogic;
signal FS2P_C31 : std_ulogic;
signal FS2P_C41 : std_ulogic;
signal FS2P_C51 : std_ulogic;
signal FS2P_C61 : std_ulogic;
signal FS2P_C71 : std_ulogic;
signal FS2P_C81 : std_ulogic;
signal N_ow_IAck_0 : std_ulogic;
signal N_ow_ShiftEnable_1 : std_ulogic;
signal N_ow_LinkOut_2 : std_ulogic;
signal N_ow_QValid_3 : std_ulogic;
signal N_FS10_4 : std_ulogic;
signal N_FS10_SSW_5 : std_ulogic;
signal N_FS10_SSR_6 : std_ulogic;
signal N_FP21_7 : std_ulogic;
signal N_FP21_SSW_8 : std_ulogic;
signal N_FP21_SSR_9 : std_ulogic;
signal N_FP151_10 : std_ulogic;
signal N_FP151_SSW_11 : std_ulogic;
signal N_FP151_SSR_12 : std_ulogic;
signal N_FS40_13 : std_ulogic;
signal N_FS40_SSW_14 : std_ulogic;
signal N_FS40_SSR_15 : std_ulogic;
signal N_FP171_16 : std_ulogic;
signal N_FP171_SSW_17 : std_ulogic;
signal N_FP171_SSR_18 : std_ulogic;
signal N_FP281_19 : std_ulogic;
signal N_FP281_SSW_20 : std_ulogic;
signal N_FP281_SSR_21 : std_ulogic;
signal N_FP281_SSW_22 : std_ulogic;
signal N_FP281_SSR_23 : std_ulogic;
signal N_FS22_24 : std_ulogic;
signal N_FS22_SSR_26 : std_ulogic;
signal N_FS3_cnd0_27 : std_ulogic;
signal N_FS3_cnd0_SSW_28 : std_ulogic;
signal N_FS3_cnd0_SSR_29 : std_ulogic;
signal N_FS3_cnd1_30 : std_ulogic;
signal N_FS3_cnd1_SSW_31 : std_ulogic;
signal N_FS3_cnd1_SSR_32 : std_ulogic;
signal N_FT9F2_33 : std_ulogic;
signal N_FT9F2_SSW_34 : std_ulogic;
signal N_FT9F2_SSR_35 : std_ulogic;
signal N_FS2P_C81_36 : std_ulogic;
signal N_FS2P_C81_SSW_37 : std_ulogic;
signal N_FS2P_C81_SSR_38 : std_ulogic;
signal PP1st0 : std_ulogic;
signal PP2st0 : std_ulogic;
signal PP11st0 : std_ulogic;
signal PP12st0 : std_ulogic;
signal PP14st0 : std_ulogic;
signal PP15st0 : std_ulogic;
signal PP16st0 : std_ulogic;
signal PP17st0 : std_ulogic;
signal PP28st0 : std_ulogic;
signal PP29st0 : std_ulogic;
signal PP2S_C0st0 : std_ulogic;
signal PP2S_C1st0 : std_ulogic;
signal PP2S_C2st0 : std_ulogic;
signal PP2S_C3st0 : std_ulogic;
signal PP2S_C4st0 : std_ulogic;
signal PP2S_C5st0 : std_ulogic;
signal PP2S_C6st0 : std_ulogic;
signal PP2S_C7st0 : std_ulogic;
signal PP2S_C8st0 : std_ulogic;
signal PP2S_C9st0 : std_ulogic;
signal PS2P_C0st0 : std_ulogic;
signal PS2P_C1st0 : std_ulogic;
signal PS2P_C2st0 : std_ulogic;
signal PS2P_C3st0 : std_ulogic;
signal PS2P_C4st0 : std_ulogic;
signal PS2P_C5st0 : std_ulogic;
signal PS2P_C6st0 : std_ulogic;
signal PS2P_C7st0 : std_ulogic;
signal PS2P_C8st0 : std_ulogic;

begin

-- I/O assignments:
S_LinkIn <= LinkIn;
S_IValid <= IValid;
S_QAck <= QAck;
S_IData <= IData;
IAck <= N_ow_IAck_0;
ShiftEnable <= N_ow_ShiftEnable_1;
LinkOut <= N_ow_LinkOut_2;
QValid <= N_ow_QValid_3;

-- code-gen (blackbox) instances (0)

-- FS10 : std_ulogic
FS10 <= (N_FS10_4 and N_FS10_SSW_5);

-- FP11 : std_ulogic
FP11 <= (PP1st0 and not PP2st0 and S_LinkIn);

-- FP21 : std_ulogic
FP21 <= (N_FP21_7 and N_FP21_SSW_8);

-- FP111 : std_ulogic
FP111 <= (PP11st0 and not PP12st0 and not S_IValid);

-- FP151 : std_ulogic
FP151 <= (N_FP151_10 and N_FP151_SSW_11);

-- FP161 : std_ulogic
FP161 <= (PP16st0 and not PP29st0 and not S_QAck);

-- FS40 : std_ulogic
FS40 <= (N_FS40_13 and N_FS40_SSW_14);

-- FP171 : std_ulogic
FP171 <= (N_FP171_16 and N_FP171_SSW_17);

-- FP281 : std_ulogic
FP281 <= (N_FP281_19 and N_FP281_SSW_20 and N_FP281_SSW_22);

-- FS2_cnd0 : std_ulogic
FS2_cnd0 <= not S_LinkIn;

-- FS2_cnd1 : std_ulogic
FS2_cnd1 <= S_LinkIn;

-- FS22 : std_ulogic
FS22 <= (N_FS22_24 and N_FP281_SSW_22);

-- FS3_cnd0 : std_ulogic
FS3_cnd0 <= (N_FS3_cnd0_27 and N_FS3_cnd0_SSW_28);

-- FS3_cnd1 : std_ulogic
FS3_cnd1 <= (N_FS3_cnd1_30 and N_FS3_cnd1_SSW_31);

-- FT9F2 : std_ulogic
FT9F2 <= (N_FT9F2_33 and N_FT9F2_SSW_34);

-- FP2S_C01 : std_ulogic
FP2S_C01 <= (PP2S_C0st0 and not PP2S_C1st0);

-- FP2S_C11 : std_ulogic
FP2S_C11 <= (PP2S_C1st0 and not PP2S_C2st0);

-- FP2S_C21 : std_ulogic
FP2S_C21 <= (PP2S_C2st0 and not PP2S_C3st0);

-- FP2S_C31 : std_ulogic
FP2S_C31 <= (PP2S_C3st0 and not PP2S_C4st0);

-- FP2S_C41 : std_ulogic
FP2S_C41 <= (PP2S_C4st0 and not PP2S_C5st0);

-- FP2S_C51 : std_ulogic
FP2S_C51 <= (PP2S_C5st0 and not PP2S_C6st0);

-- FP2S_C61 : std_ulogic
FP2S_C61 <= (PP2S_C6st0 and not PP2S_C7st0);

-- FP2S_C71 : std_ulogic
FP2S_C71 <= (PP2S_C7st0 and not PP2S_C8st0);

-- FP2S_C81 : std_ulogic
FP2S_C81 <= (PP2S_C8st0 and not PP2S_C9st0);

-- FS2P_C01 : std_ulogic
FS2P_C01 <= (PS2P_C0st0 and not PS2P_C1st0);

-- FS2P_C11 : std_ulogic
FS2P_C11 <= (PS2P_C1st0 and not PS2P_C2st0);

-- FS2P_C21 : std_ulogic
FS2P_C21 <= (PS2P_C2st0 and not PS2P_C3st0);

-- FS2P_C31 : std_ulogic
FS2P_C31 <= (PS2P_C3st0 and not PS2P_C4st0);

-- FS2P_C41 : std_ulogic
FS2P_C41 <= (PS2P_C4st0 and not PS2P_C5st0);

-- FS2P_C51 : std_ulogic
FS2P_C51 <= (PS2P_C5st0 and not PS2P_C6st0);

-- FS2P_C61 : std_ulogic
FS2P_C61 <= (PS2P_C6st0 and not PS2P_C7st0);

-- FS2P_C71 : std_ulogic
FS2P_C71 <= (PS2P_C7st0 and not PS2P_C8st0);

-- FS2P_C81 : std_ulogic
FS2P_C81 <= (N_FS2P_C81_36 and N_FS2P_C81_SSW_37);

-- N_ow_IAck_0 : std_ulogic
N_ow_IAck_0 <= FP281;

-- N_ow_ShiftEnable_1 : std_ulogic
N_ow_ShiftEnable_1 <= (FS2P_C01 or FS2P_C11 or FS2P_C21 or FS2P_C31 or FS2P_C41 or FS2P_C51 or FS2P_C61 or FS2P_C71);

-- N_ow_LinkOut_2 : std_ulogic
N_ow_LinkOut_2 <= (FP2S_C01 or FS3_cnd1 or FS3_cnd0 or (FP2S_C11 and S_IData(0)) or (FP2S_C21 and S_IData(1)) or (FP2S_C31 and S_IData(2)) or (FP2S_C41 and S_IData(3)) or (FP2S_C51 and S_IData(4)) or (FP2S_C61 and S_IData(5)) or (FP2S_C71 and S_IData(6)) or (FP2S_C81 and S_IData(7)));

-- N_ow_QValid_3 : std_ulogic
N_ow_QValid_3 <= PP14st0;

-- N_FS10_4 : std_ulogic
N_FS10_4 <= not PP1st0;

-- N_FS10_SSW_5 : std_ulogic
N_FS10_SSW_5 <= (N_FP281_SSR_21 or N_FS2P_C81_SSR_38);

-- N_FS10_SSR_6 : std_ulogic
N_FS10_SSR_6 <= N_FS10_4;

-- N_FP21_7 : std_ulogic
N_FP21_7 <= PP2st0;

-- N_FP21_SSW_8 : std_ulogic
N_FP21_SSW_8 <= (N_FP281_SSR_23 or N_FS22_SSR_26);

-- N_FP21_SSR_9 : std_ulogic
N_FP21_SSR_9 <= N_FP21_7;

-- N_FP151_10 : std_ulogic
N_FP151_10 <= (PP15st0 and not PP16st0 and S_QAck);

-- N_FP151_SSW_11 : std_ulogic
N_FP151_SSW_11 <= (N_FS40_SSR_15 and not N_FT9F2_SSR_35);

-- N_FP151_SSR_12 : std_ulogic
N_FP151_SSR_12 <= N_FP151_10;

-- N_FS40_13 : std_ulogic
N_FS40_13 <= not PP17st0;

-- N_FS40_SSW_14 : std_ulogic
N_FS40_SSW_14 <= (N_FT9F2_SSR_35 or N_FP151_SSR_12);

-- N_FS40_SSR_15 : std_ulogic
N_FS40_SSR_15 <= N_FS40_13;

-- N_FP171_16 : std_ulogic
N_FP171_16 <= PP17st0;

-- N_FP171_SSW_17 : std_ulogic
N_FP171_SSW_17 <= (N_FS3_cnd0_SSR_29 or N_FS3_cnd1_SSR_32);

-- N_FP171_SSR_18 : std_ulogic
N_FP171_SSR_18 <= N_FP171_16;

-- N_FP281_19 : std_ulogic
N_FP281_19 <= (PP28st0 and not PP11st0 and FS2_cnd0);

-- N_FP281_SSW_20 : std_ulogic
N_FP281_SSW_20 <= N_FS10_SSR_6;

-- N_FP281_SSR_21 : std_ulogic
N_FP281_SSR_21 <= (N_FP281_19 and N_FP281_SSW_22);

-- N_FP281_SSW_22 : std_ulogic
N_FP281_SSW_22 <= N_FP21_SSR_9;

-- N_FP281_SSR_23 : std_ulogic
N_FP281_SSR_23 <= (N_FP281_19 and N_FP281_SSW_20);

-- N_FS22_24 : std_ulogic
N_FS22_24 <= (FS2_cnd1 and not PS2P_C0st0);

-- N_FS22_SSR_26 : std_ulogic
N_FS22_SSR_26 <= N_FS22_24;

-- N_FS3_cnd0_27 : std_ulogic
N_FS3_cnd0_27 <= (PP14st0 and not PP15st0);

-- N_FS3_cnd0_SSW_28 : std_ulogic
N_FS3_cnd0_SSW_28 <= N_FP171_SSR_18;

-- N_FS3_cnd0_SSR_29 : std_ulogic
N_FS3_cnd0_SSR_29 <= N_FS3_cnd0_27;

-- N_FS3_cnd1_30 : std_ulogic
N_FS3_cnd1_30 <= (S_IValid and not PP2S_C0st0 and PP12st0);

-- N_FS3_cnd1_SSW_31 : std_ulogic
N_FS3_cnd1_SSW_31 <= (N_FP171_SSR_18 and not N_FS3_cnd0_SSR_29);

-- N_FS3_cnd1_SSR_32 : std_ulogic
N_FS3_cnd1_SSR_32 <= N_FS3_cnd1_30;

-- N_FT9F2_33 : std_ulogic
N_FT9F2_33 <= (not PP28st0 and PP2S_C9st0);

-- N_FT9F2_SSW_34 : std_ulogic
N_FT9F2_SSW_34 <= N_FS40_SSR_15;

-- N_FT9F2_SSR_35 : std_ulogic
N_FT9F2_SSR_35 <= N_FT9F2_33;

-- N_FS2P_C81_36 : std_ulogic
N_FS2P_C81_36 <= (PS2P_C8st0 and not PP14st0 and PP29st0);

-- N_FS2P_C81_SSW_37 : std_ulogic
N_FS2P_C81_SSW_37 <= (N_FS10_SSR_6 and not N_FP281_SSR_21);

-- N_FS2P_C81_SSR_38 : std_ulogic
N_FS2P_C81_SSR_38 <= N_FS2P_C81_36;

all_ffs: process (clk) is
begin
    if rising_edge(clk) then
        if to_bool(rst) then
            PP1st0 <= '1';
            PP2st0 <= '0';
            PP11st0 <= '0';
            PP12st0 <= '1';
            PP14st0 <= '0';
            PP15st0 <= '0';
            PP16st0 <= '0';
            PP17st0 <= '1';
            PP28st0 <= '0';
            PP29st0 <= '1';
            PP2S_C0st0 <= '0';
            PP2S_C1st0 <= '0';
            PP2S_C2st0 <= '0';
            PP2S_C3st0 <= '0';
            PP2S_C4st0 <= '0';
            PP2S_C5st0 <= '0';
            PP2S_C6st0 <= '0';
            PP2S_C7st0 <= '0';
            PP2S_C8st0 <= '0';
            PP2S_C9st0 <= '0';
            PS2P_C0st0 <= '0';
            PS2P_C1st0 <= '0';
            PS2P_C2st0 <= '0';
            PS2P_C3st0 <= '0';
            PS2P_C4st0 <= '0';
            PS2P_C5st0 <= '0';
            PS2P_C6st0 <= '0';
            PS2P_C7st0 <= '0';
            PS2P_C8st0 <= '0';
        else
            if to_bool((FS2P_C81 or not PS2P_C8st0)) then
                PS2P_C8st0 <= FS2P_C71;
            end if;
            if to_bool((FS2P_C71 or not PS2P_C7st0)) then
                PS2P_C7st0 <= FS2P_C61;
            end if;
            if to_bool((FS2P_C61 or not PS2P_C6st0)) then
                PS2P_C6st0 <= FS2P_C51;
            end if;
            if to_bool((FS2P_C51 or not PS2P_C5st0)) then
                PS2P_C5st0 <= FS2P_C41;
            end if;
            if to_bool((FS2P_C41 or not PS2P_C4st0)) then
                PS2P_C4st0 <= FS2P_C31;
            end if;
            if to_bool((FS2P_C31 or not PS2P_C3st0)) then
                PS2P_C3st0 <= FS2P_C21;
            end if;
            if to_bool((FS2P_C21 or not PS2P_C2st0)) then
                PS2P_C2st0 <= FS2P_C11;
            end if;
            if to_bool((FS2P_C11 or not PS2P_C1st0)) then
                PS2P_C1st0 <= FS2P_C01;
            end if;
            if to_bool((FS2P_C01 or not PS2P_C0st0)) then
                PS2P_C0st0 <= FS22;
            end if;
            if to_bool((FT9F2 or not PP2S_C9st0)) then
                PP2S_C9st0 <= FP2S_C81;
            end if;
            if to_bool((FP2S_C81 or not PP2S_C8st0)) then
                PP2S_C8st0 <= FP2S_C71;
            end if;
            if to_bool((FP2S_C71 or not PP2S_C7st0)) then
                PP2S_C7st0 <= FP2S_C61;
            end if;
            if to_bool((FP2S_C61 or not PP2S_C6st0)) then
                PP2S_C6st0 <= FP2S_C51;
            end if;
            if to_bool((FP2S_C51 or not PP2S_C5st0)) then
                PP2S_C5st0 <= FP2S_C41;
            end if;
            if to_bool((FP2S_C41 or not PP2S_C4st0)) then
                PP2S_C4st0 <= FP2S_C31;
            end if;
            if to_bool((FP2S_C31 or not PP2S_C3st0)) then
                PP2S_C3st0 <= FP2S_C21;
            end if;
            if to_bool((FP2S_C21 or not PP2S_C2st0)) then
                PP2S_C2st0 <= FP2S_C11;
            end if;
            if to_bool((FP2S_C11 or not PP2S_C1st0)) then
                PP2S_C1st0 <= FP2S_C01;
            end if;
            if to_bool((FP2S_C01 or not PP2S_C0st0)) then
                PP2S_C0st0 <= FS3_cnd1;
            end if;
            if to_bool((FS2P_C81 or not PP29st0)) then
                PP29st0 <= FP161;
            end if;
            if to_bool((FP281 or not PP28st0)) then
                PP28st0 <= FT9F2;
            end if;
            if to_bool((FP171 or not PP17st0)) then
                PP17st0 <= FS40;
            end if;
            if to_bool((FP161 or not PP16st0)) then
                PP16st0 <= FP151;
            end if;
            if to_bool((FP151 or not PP15st0)) then
                PP15st0 <= FS3_cnd0;
            end if;
            if to_bool((FS3_cnd0 or not PP14st0)) then
                PP14st0 <= FS2P_C81;
            end if;
            if to_bool((FS3_cnd1 or not PP12st0)) then
                PP12st0 <= FP111;
            end if;
            if to_bool((FP111 or not PP11st0)) then
                PP11st0 <= FP281;
            end if;
            if to_bool((FP21 or not PP2st0)) then
                PP2st0 <= FP11;
            end if;
            if to_bool((FP11 or not PP1st0)) then
                PP1st0 <= FS10;
            end if;
        end if;
    end if;
end process;
end architecture rtl;
