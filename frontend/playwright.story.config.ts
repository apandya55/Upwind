import { defineConfig } from '@playwright/test';
export default defineConfig({testDir:'./tests',workers:1,timeout:120000,expect:{timeout:30000},use:{baseURL:'http://127.0.0.1:5174',viewport:{width:1440,height:900},launchOptions:{args:['--no-sandbox']},screenshot:'only-on-failure'}});
