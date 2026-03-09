/**
 * Seed realistic sample data into Firestore for testing the admin panel.
 * Creates a sample family with children, tasks, completions, XP, messages, etc.
 */
import { doc, setDoc } from "firebase/firestore";
import { db } from "./firebase";
import { registerFamily } from "./firestore";

const FAMILY_ID = "DEMO01";
const FAMILY_NAME = "משפחת כהן";

function generateId(): string {
  return Math.random().toString(36).slice(2, 10);
}

function daysAgo(n: number): number {
  return Date.now() - n * 86400000;
}

function getWeekKey(d: Date): string {
  const start = new Date(d.getFullYear(), 0, 1);
  const diff = d.getTime() - start.getTime();
  const weekNum = Math.ceil(diff / 604800000 + 1);
  return `${d.getFullYear()}-W${String(weekNum).padStart(2, "0")}`;
}

function getDateKey(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export async function seedSampleData(): Promise<string> {
  const basePath = `families/${FAMILY_ID}/data`;

  // 1. Family config
  const familyConfig = {
    family: {
      "אבא": { name: "אבא", role: "parent", emoji: "👨", color: "#3B82F6", weeklyPay: 0 },
      "אמא": { name: "אמא", role: "parent", emoji: "👩", color: "#EC4899", weeklyPay: 0 },
      "יובל": { name: "יובל", role: "child", emoji: "👦", color: "#10B981", weeklyPay: 20 },
      "נועה": { name: "נועה", role: "child", emoji: "👧", color: "#F59E0B", weeklyPay: 15 },
      "עידו": { name: "עידו", role: "child", emoji: "🧒", color: "#8B5CF6", weeklyPay: 10 },
    },
    children: ["יובל", "נועה", "עידו"],
    pins: { "אבא": "1111", "אמא": "2222" },
    familyName: FAMILY_NAME,
    familyId: FAMILY_ID,
  };

  // 2. Tasks
  const tasks = [
    { id: "t1", title: "סידור חדר", icon: "🛏️", weight: 2, assignedTo: ["יובל", "נועה", "עידו"], bonus: false, type: "personal" },
    { id: "t2", title: "שטיפת כלים", icon: "🍽️", weight: 3, assignedTo: ["יובל", "נועה"], bonus: false, type: "shared" },
    { id: "t3", title: "הוצאת זבל", icon: "🗑️", weight: 2, assignedTo: ["יובל", "עידו"], bonus: false, type: "shared" },
    { id: "t4", title: "שיעורי בית", icon: "📚", weight: 3, assignedTo: ["יובל", "נועה", "עידו"], bonus: false, type: "personal" },
    { id: "t5", title: "טיול עם הכלב", icon: "🐕", weight: 2, assignedTo: ["נועה", "עידו"], bonus: false, type: "shared" },
    { id: "t6", title: "עזרה בבישול", icon: "🍳", weight: 4, assignedTo: ["יובל", "נועה"], bonus: true, type: "shared" },
    { id: "t7", title: "קיפול כביסה", icon: "👕", weight: 2, assignedTo: ["יובל", "נועה", "עידו"], bonus: false, type: "personal" },
    { id: "t8", title: "ניקוי שולחן", icon: "🧹", weight: 1, assignedTo: ["עידו"], bonus: false, type: "personal" },
  ];

  // 3. Completions (last 6 weeks of data)
  const completions: Record<string, any> = {};
  const children = ["יובל", "נועה", "עידו"];
  const now = new Date();

  for (let weekOffset = 0; weekOffset < 6; weekOffset++) {
    const weekDate = new Date(now.getTime() - weekOffset * 7 * 86400000);
    const wk = getWeekKey(weekDate);

    for (const task of tasks) {
      for (const child of task.assignedTo) {
        for (let dayOff = 0; dayOff < 7; dayOff++) {
          const dayDate = new Date(weekDate.getTime() - dayOff * 86400000);
          const dateStr = getDateKey(dayDate);
          const done = Math.random() > 0.3; // 70% completion rate
          const key = `${wk}::${dateStr}::${task.id}::${child}`;
          completions[key] = {
            done,
            approved: done ? Math.random() > 0.2 : false,
            approvedBy: done ? (Math.random() > 0.5 ? "אבא" : "אמא") : undefined,
            ts: dayDate.getTime() + Math.floor(Math.random() * 43200000),
          };
        }
      }
    }
  }

  // 4. XP
  const xp: Record<string, number> = {
    "יובל": 1250,
    "נועה": 980,
    "עידו": 720,
  };

  const totalXpEarned: Record<string, number> = {
    "יובל": 2100,
    "נועה": 1650,
    "עידו": 1100,
  };

  // 5. Streaks
  const streaks: Record<string, number> = {
    "יובל": 5,
    "נועה": 3,
    "עידו": 7,
  };

  // 6. Approved counts
  const approvedCount: Record<string, number> = {
    "יובל": 142,
    "נועה": 118,
    "עידו": 89,
  };

  // 7. Earned badges
  const earnedBadges: Record<string, any[]> = {
    "יובל": [
      { id: "first_task", ts: daysAgo(40) },
      { id: "streak_3", ts: daysAgo(35) },
      { id: "streak_7", ts: daysAgo(20) },
      { id: "xp_500", ts: daysAgo(25) },
      { id: "xp_1000", ts: daysAgo(10) },
    ],
    "נועה": [
      { id: "first_task", ts: daysAgo(38) },
      { id: "streak_3", ts: daysAgo(30) },
      { id: "xp_500", ts: daysAgo(20) },
    ],
    "עידו": [
      { id: "first_task", ts: daysAgo(36) },
      { id: "streak_3", ts: daysAgo(28) },
      { id: "streak_7", ts: daysAgo(15) },
      { id: "xp_500", ts: daysAgo(18) },
    ],
  };

  // 8. Messages (wall)
  const messages = [
    { id: generateId(), from: "אמא", to: "wall", text: "כל הכבוד יובל על סידור החדר! 🌟", type: "praise", ts: daysAgo(0) },
    { id: generateId(), from: "אבא", to: "נועה", text: "בונוס על עזרה בבישול!", type: "bonus", ts: daysAgo(1) },
    { id: generateId(), from: "system", to: "wall", text: "עידו השיג רצף של 7 ימים! 🔥", type: "system", ts: daysAgo(2) },
    { id: generateId(), from: "אמא", to: "wall", text: "שבת שלום למשפחה! 💝", type: "free", ts: daysAgo(3) },
    { id: generateId(), from: "אבא", to: "יובל", text: "תזכור לעשות שיעורי בית", type: "nudge", ts: daysAgo(4) },
    { id: generateId(), from: "נועה", to: "wall", text: "סיימתי את כל המטלות! 🎉", type: "free", ts: daysAgo(5) },
    { id: generateId(), from: "אמא", to: "wall", text: "יובל עזר בבישול ארוחת ערב", type: "praise", ts: daysAgo(6) },
    { id: generateId(), from: "system", to: "wall", text: "סיכום שבועי: 85% השלמה!", type: "system", ts: daysAgo(7) },
    { id: generateId(), from: "אבא", to: "עידו", text: "בונוס על ניקיון מיוחד", type: "bonus", ts: daysAgo(8) },
    { id: generateId(), from: "אמא", to: "wall", text: "כל הילדים עשו מצוין השבוע!", type: "praise", ts: daysAgo(10) },
    { id: generateId(), from: "system", to: "wall", text: "נועה השיגה תג חדש: XP 500!", type: "system", ts: daysAgo(12) },
    { id: generateId(), from: "אבא", to: "wall", text: "טיול משפחתי ביום שישי 🌳", type: "free", ts: daysAgo(14) },
  ];

  // 9. Penalties
  const penalties = [
    { id: generateId(), childId: "יובל", title: "לא סידר חדר", icon: "⚠️", xp: 50, ts: daysAgo(12), by: "אבא" },
    { id: generateId(), childId: "נועה", title: "ויכוח", icon: "😤", xp: 30, ts: daysAgo(18), by: "אמא" },
    { id: generateId(), childId: "עידו", title: "לא עשה שיעורים", icon: "📝", xp: 40, ts: daysAgo(25), by: "אבא" },
  ];

  // 10. Audit log
  const auditActions = [
    "task_done", "task_approved", "xp_granted", "badge_earned", "message_sent",
    "penalty_added", "reward_purchased", "streak_achieved", "task_done", "task_approved",
  ];
  const auditLog: any[] = [];
  for (let i = 0; i < 50; i++) {
    const child = children[Math.floor(Math.random() * children.length)];
    const action = auditActions[Math.floor(Math.random() * auditActions.length)];
    const parent = Math.random() > 0.5 ? "אבא" : "אמא";
    auditLog.push({
      id: generateId(),
      action,
      by: action.includes("approved") || action.includes("penalty") ? parent : child,
      ts: daysAgo(Math.floor(Math.random() * 42)),
      details: `${child} — ${tasks[Math.floor(Math.random() * tasks.length)].title}`,
    });
  }
  auditLog.sort((a, b) => b.ts - a.ts);

  // 11. Challenges
  const wk = getWeekKey(now);
  const challenges = [
    { id: generateId(), title: "אתגר משפחתי", desc: "כל הילדים משלימים 100% מהמטלות", emoji: "🏆", type: "family", condition: "completion_pct", value: 100, xpReward: 200, week: wk },
    { id: generateId(), title: "רצף 5 ימים", desc: "השלם מטלות 5 ימים רצוף", emoji: "🔥", type: "individual", condition: "streak", value: 5, xpReward: 100, week: wk },
    { id: generateId(), title: "עוזר בבישול", desc: "עזור בבישול 3 פעמים השבוע", emoji: "👨‍🍳", type: "individual", condition: "task_count", value: 3, xpReward: 75, week: wk },
  ];

  // 12. Rewards
  const rewards = [
    { id: generateId(), title: "שעה נוספת מסכים", icon: "📱", cost: 100, active: true },
    { id: generateId(), title: "גלידה", icon: "🍦", cost: 50, active: true },
    { id: generateId(), title: "בחירת סרט משפחתי", icon: "🎬", cost: 150, active: true },
    { id: generateId(), title: "טיול לפארק", icon: "🎡", cost: 200, active: true },
    { id: generateId(), title: "צעצוע קטן", icon: "🧸", cost: 500, active: true },
  ];

  // 13. Purchase history
  const purchaseHistory = [
    { id: generateId(), rewardId: rewards[0].id, rewardTitle: rewards[0].title, childId: "יובל", cost: 100, ts: daysAgo(5), status: "fulfilled" },
    { id: generateId(), rewardId: rewards[1].id, rewardTitle: rewards[1].title, childId: "נועה", cost: 50, ts: daysAgo(8), status: "fulfilled" },
    { id: generateId(), rewardId: rewards[2].id, rewardTitle: rewards[2].title, childId: "יובל", cost: 150, ts: daysAgo(14), status: "fulfilled" },
    { id: generateId(), rewardId: rewards[0].id, rewardTitle: rewards[0].title, childId: "עידו", cost: 100, ts: daysAgo(3), status: "pending" },
  ];

  // 14. Spent XP
  const spentXp: Record<string, number> = {
    "יובל": 850,
    "נועה": 670,
    "עידו": 380,
  };

  // ── Write all data to Firestore ──
  const dataToWrite: Record<string, any> = {
    "family-config": JSON.stringify(familyConfig),
    "tasks": JSON.stringify(tasks),
    "completions": JSON.stringify(completions),
    "xp": JSON.stringify(xp),
    "totalXpEarned": JSON.stringify(totalXpEarned),
    "streaks": JSON.stringify(streaks),
    "approvedCount": JSON.stringify(approvedCount),
    "earnedBadges": JSON.stringify(earnedBadges),
    "messages": JSON.stringify(messages),
    "penalties": JSON.stringify(penalties),
    "auditLog": JSON.stringify(auditLog),
    "challenges": JSON.stringify(challenges),
    "rewards": JSON.stringify(rewards),
    "purchaseHistory": JSON.stringify(purchaseHistory),
    "spentXp": JSON.stringify(spentXp),
    "goals": JSON.stringify([]),
    "calEvents": JSON.stringify([]),
    "exams": JSON.stringify([]),
    "groceries": JSON.stringify([]),
    "avatars": JSON.stringify({}),
    "childReminders": JSON.stringify({}),
    "locations": JSON.stringify({}),
    "swaps": JSON.stringify([]),
    "customChallenges": JSON.stringify([]),
    "taskTemplates": JSON.stringify([]),
  };

  for (const [key, value] of Object.entries(dataToWrite)) {
    await setDoc(doc(db, basePath, key), {
      value,
      updatedAt: new Date().toISOString(),
    });
  }

  // Register in admin registry
  await registerFamily(FAMILY_ID, {
    familyName: FAMILY_NAME,
    memberCount: 5,
    childCount: 3,
    source: "seed",
  });

  return FAMILY_ID;
}
