library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library ftl;
use ftl.ftlbase.all;

package myutils is

subtype dfu_opcode_t is std_logic_vector(4 downto 0);
subtype dfu_veclen_t is std_logic_vector(9 downto 0);

subtype raw_dfu_config_t is std_logic_vector(14 downto 0);

type dfu_config_t is record
    opcode      : dfu_opcode_t;         --! DFU command operation code
    veclen      : dfu_veclen_t;         --! vector length
end record;

type dfu_ctrlreg_t is record
    cfg         : dfu_config_t;
    idx         : dfu_veclen_t;
    p_idx       : dfu_veclen_t;
end record;

constant ZERO_dfu_config_t : dfu_config_t := (
    opcode => (others => '0'),
    veclen => (others => '0')
);
constant ZERO_dfu_ctrlreg_t : dfu_ctrlreg_t := (
    cfg => ZERO_dfu_config_t,
    idx => (others => '0'), p_idx => (others => '0')
);

constant UNDEF_dfu_ctrlreg_t : dfu_ctrlreg_t := ZERO_dfu_ctrlreg_t;

-- 


-- counter
function minus(D: std_logic_vector; P: std_ulogic) return std_logic_vector;
function minus(D: std_logic_vector) return std_logic_vector;

function is_nonzero(D: std_logic_vector(7 downto 0)) return std_ulogic;

-- folder
function concat(D1: std_logic_vector; D2: std_logic_vector; P: std_ulogic) return std_logic_vector;
function take_first(D1: std_logic_vector; D2: std_logic_vector; P: std_ulogic) return std_logic_vector;

function adder_stage(DI: std_logic_vector; P: std_ulogic) return std_logic_vector;

function nop1(DI: std_logic_vector; P: std_ulogic) return std_logic_vector;
function nop2(DI: std_logic_vector; P: std_ulogic) return std_logic_vector;

function extend_inp_null(DI: std_logic_vector(31 downto 0); P: std_ulogic) return std_logic_vector;
function give_neutral(ctc: dfu_ctrlreg_t) return std_logic_vector;
function extend_inp_ctr(DA: std_logic_vector(31 downto 0); ctr: dfu_ctrlreg_t; P: std_ulogic) return std_logic_vector;
function init_ctr(DI: raw_dfu_config_t; P: std_ulogic) return dfu_ctrlreg_t;
function update_ctr(DI: dfu_ctrlreg_t; P: std_ulogic) return dfu_ctrlreg_t;
function is_reduction(DI: dfu_ctrlreg_t) return std_ulogic;
function is_continuing(DI: dfu_ctrlreg_t) return std_ulogic;

end;

package body myutils is

function minus(D: std_logic_vector; P: std_ulogic) return std_logic_vector is
constant len : integer := D'length;
variable res : std_logic_vector(len downto 0);      -- wider
begin
    res := std_logic_vector( to_signed(to_integer(signed(D)) - 1, len+1) );
    return res(len-1 downto 0);
end function minus;

function minus(D: std_logic_vector) return std_logic_vector is
constant len : integer := D'length;
variable res : std_logic_vector(len downto 0);      -- wider
begin
    res := std_logic_vector( to_signed(to_integer(signed(D)) - 1, len+1) );
    return res(len-1 downto 0);
end function minus;


function is_nonzero(D: std_logic_vector(7 downto 0)) return std_ulogic is
begin
    if D /= zero_std_logic_vector(7, 0) then
        return '1';
    else
        return '0';
    end if;
end function is_nonzero;


function concat(D1: std_logic_vector; D2: std_logic_vector; P: std_ulogic) return std_logic_vector is
variable D : std_logic_vector((D1'length + D2'length - 1) downto 0);
begin
	D := D1 & D2;
	return D;
end function concat;

function take_first(D1: std_logic_vector; D2: std_logic_vector; P: std_ulogic) return std_logic_vector is
begin
    return D1;
end function;


function adder_stage(DI: std_logic_vector; P: std_ulogic) return std_logic_vector is
variable DO : std_logic_vector((DI'length/2 -1) downto 0);
variable a, b : integer;
begin
	a := to_integer(signed(DI(DI'length-1 downto DI'length/2)));
	b := to_integer(signed(DI(DI'length/2-1 downto 0)));
	DO := std_logic_vector(to_signed(a + b, DI'length/2));
	return DO;
end function adder_stage;

function nop1(DI: std_logic_vector; P: std_ulogic) return std_logic_vector is
begin
    return DI;
end function;

function nop2(DI: std_logic_vector; P: std_ulogic) return std_logic_vector is
begin
    return DI;
end function;

function extend_inp_null(DI: std_logic_vector(31 downto 0); P: std_ulogic) return std_logic_vector is
variable v : std_logic_vector(41 downto 0);
begin
    v := (others => '0');
    v(31 downto 0) := DI;
    return v;
end function;

function give_neutral(ctc: dfu_ctrlreg_t) return std_logic_vector is
variable v : std_logic_vector(41 downto 0);
begin
-- ctc.cfg.opcode(4 downto 0)
--      RIMmS             neutral
--     "00000"     add -> 0
--     "00001"     sub -> 0
--     "10000"     sum -> 0
--     "10011"     min -> +inf
--     "10101"     max -> -inf
--     "11011"     idxmin -> +inf
--     "11101"     idxmax -> -inf
    v := (others => '0');
    if ctc.cfg.opcode(2 downto 1) = "01" then
        -- +inf
        -- v(31 downto 0) := x"7FFFffff";
        v(31 downto 0) := x"7FFF0000";
    elsif ctc.cfg.opcode(2 downto 1) = "10" then
        -- -inf
        -- v(31 downto 0) := x"80000000";
        v(31 downto 0) := x"8000ffff";
    end if;
    -- TODO
    --v(31 downto 0) := DI;
    return v;
end function;

function extend_inp_ctr(DA: std_logic_vector(31 downto 0); ctr: dfu_ctrlreg_t; P: std_ulogic) return std_logic_vector is
variable v : std_logic_vector(41 downto 0);
begin
    v := (others => '0');
    v(31 downto 0) := DA;
    v(41 downto 32) := ctr.p_idx;
    return v;
end function;

function init_ctr(DI: raw_dfu_config_t; P: std_ulogic) return dfu_ctrlreg_t is
variable v : dfu_ctrlreg_t;
begin
    v := ZERO_dfu_ctrlreg_t;
    v.cfg.opcode := DI(14 downto 10);
    v.cfg.veclen := DI(9 downto 0);
    return v;
end function;

function update_ctr(DI: dfu_ctrlreg_t; P: std_ulogic) return dfu_ctrlreg_t is
variable v : dfu_ctrlreg_t;
begin
    v := DI;
    v.p_idx := v.idx;
    v.idx := std_logic_vector(to_unsigned( to_integer(unsigned(v.idx)) + 1,  dfu_veclen_t'length));
    return v;
end function;

function is_reduction(DI: dfu_ctrlreg_t) return std_ulogic is
begin
    return DI.cfg.opcode(4);
end function;

function is_continuing(DI: dfu_ctrlreg_t) return std_ulogic is
begin
    if DI.cfg.veclen /= DI.idx then
        return '1';
    else
        return '0';
    end if;
end function;

end;
