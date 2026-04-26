import { initializeApp } from "https://www.gstatic.com/firebasejs/11.7.1/firebase-app.js";
import {
  getAnalytics,
  isSupported as isAnalyticsSupported,
} from "https://www.gstatic.com/firebasejs/11.7.1/firebase-analytics.js";
import {
  createUserWithEmailAndPassword,
  getAuth,
  signInWithEmailAndPassword,
  updateProfile,
} from "https://www.gstatic.com/firebasejs/11.7.1/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyDXEK8vjmKNKKkYG4ZtoLcGG0gDqN1bVEs",
  authDomain: "koru-41307.firebaseapp.com",
  projectId: "koru-41307",
  storageBucket: "koru-41307.firebasestorage.app",
  messagingSenderId: "580787181791",
  appId: "1:580787181791:web:25488833ab906df012716a",
  measurementId: "G-SHBNJ75VGD",
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

isAnalyticsSupported()
  .then((supported) => {
    if (supported) {
      getAnalytics(app);
    }
  })
  .catch(() => {
    // Ignore analytics setup failures in unsupported environments.
  });

// Optional: expose app globally for future Firebase product integrations.
window.koruFirebaseApp = app;
window.koruFirebaseAuth = auth;
window.koruFirebaseAuthApi = {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  updateProfile,
};
