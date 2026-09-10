import {describe,expect,it} from 'vitest';import {localDateValue} from './date'
describe('localDateValue',()=>{it('uses local calendar fields without UTC rollover',()=>{expect(localDateValue(new Date(2026,8,11,0,5))).toBe('2026-09-11')})})
