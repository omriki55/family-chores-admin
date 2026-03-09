import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyCul6puRpPx0ybOhu4xyLLUbBIPifJlZVc",
  authDomain: "family-chores-8c032.firebaseapp.com",
  projectId: "family-chores-8c032",
  storageBucket: "family-chores-8c032.firebasestorage.app",
  messagingSenderId: "500888915341",
  appId: "1:500888915341:web:37e70c52f63460cc2881c4",
};

export const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
export const auth = getAuth(app);
