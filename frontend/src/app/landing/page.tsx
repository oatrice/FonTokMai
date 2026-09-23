"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import {
  CloudRain,
  Radar,
  Bell,
  MapPin,
  BarChart3,
  Zap,
  Shield,
  Globe,
  ArrowRight,
  ChevronDown,
  CheckCircle,
  Activity,
  Clock,
  Users,
  Building2,
  Plane,
  Truck,
  Leaf,
} from "lucide-react";

// ─── Animation Variants ────────────────────────────────────────────────────────

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 32 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } },
};

const staggerContainer: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12 } },
};

// ─── Radar Animation Component ─────────────────────────────────────────────────

function RadarPulse() {
  return (
    <div className="relative w-64 h-64 sm:w-80 sm:h-80 mx-auto">
      {/* Outer rings */}
      {[1, 2, 3].map((i) => (
        <motion.div
          key={i}
          className="absolute inset-0 rounded-full border border-cyan-500/20"
          style={{ inset: `${i * 18}%` }}
          animate={{ opacity: [0.2, 0.5, 0.2] }}
          transition={{ duration: 3, delay: i * 0.4, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
      {/* Sweep line */}
      <motion.div
        className="absolute inset-0 rounded-full overflow-hidden"
        style={{ background: "transparent" }}
      >
        <motion.div
          className="absolute top-1/2 left-1/2 origin-left"
          style={{
            width: "50%",
            height: "2px",
            background: "linear-gradient(90deg, rgba(6,182,212,0.8) 0%, transparent 100%)",
            transformOrigin: "left center",
            marginTop: "-1px",
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
        />
      </motion.div>
      {/* Center dot */}
      <div className="absolute inset-0 flex items-center justify-center">
        <motion.div
          className="w-3 h-3 rounded-full bg-cyan-400"
          animate={{ scale: [1, 1.5, 1], opacity: [1, 0.6, 1] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
      {/* Rain dots scattered */}
      {[
        { top: "25%", left: "45%", delay: 0 },
        { top: "35%", left: "30%", delay: 0.5 },
        { top: "60%", left: "55%", delay: 1 },
        { top: "50%", left: "65%", delay: 1.5 },
        { top: "70%", left: "35%", delay: 0.8 },
        { top: "40%", left: "60%", delay: 1.2 },
      ].map((dot, i) => (
        <motion.div
          key={i}
          className="absolute w-2 h-2 rounded-full bg-blue-400/70"
          style={{ top: dot.top, left: dot.left }}
          animate={{ opacity: [0.3, 0.9, 0.3], scale: [0.8, 1.2, 0.8] }}
          transition={{ duration: 2.5, delay: dot.delay, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}

// ─── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({ value, label, sub }: { value: string; label: string; sub?: string }) {
  return (
    <motion.div
      variants={fadeUp}
      className="glass-panel rounded-2xl p-6 text-center"
    >
      <div className="text-3xl sm:text-4xl font-bold text-cyan-400 mb-1">{value}</div>
      <div className="text-white font-semibold text-sm sm:text-base">{label}</div>
      {sub && <div className="text-slate-400 text-xs mt-1">{sub}</div>}
    </motion.div>
  );
}

// ─── Feature Card ──────────────────────────────────────────────────────────────

function FeatureCard({
  icon: Icon,
  titleTh,
  titleEn,
  descTh,
  descEn,
}: {
  icon: React.ElementType;
  titleTh: string;
  titleEn: string;
  descTh: string;
  descEn: string;
}) {
  return (
    <motion.div
      variants={fadeUp}
      className="glass-panel glass-panel-interactive rounded-2xl p-6 cursor-default"
    >
      <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mb-4">
        <Icon className="w-6 h-6 text-cyan-400" />
      </div>
      <h3 className="font-semibold text-white text-base mb-0.5">{titleTh}</h3>
      <p className="text-xs text-slate-400 mb-3 font-medium">{titleEn}</p>
      <p className="text-slate-300 text-sm leading-relaxed">{descTh}</p>
      <p className="text-slate-500 text-xs mt-1 leading-relaxed">{descEn}</p>
    </motion.div>
  );
}

// ─── Use Case Card ─────────────────────────────────────────────────────────────

function UseCaseCard({
  icon: Icon,
  sectorTh,
  sectorEn,
  benefitTh,
  benefitEn,
  color,
}: {
  icon: React.ElementType;
  sectorTh: string;
  sectorEn: string;
  benefitTh: string;
  benefitEn: string;
  color: string;
}) {
  return (
    <motion.div
      variants={fadeUp}
      className="glass-panel glass-panel-interactive rounded-2xl p-5 cursor-default"
    >
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center mb-3"
        style={{ background: `${color}20`, border: `1px solid ${color}30` }}
      >
        <Icon className="w-5 h-5" style={{ color }} />
      </div>
      <h4 className="text-white font-semibold text-sm">{sectorTh}</h4>
      <p className="text-slate-500 text-xs mb-2">{sectorEn}</p>
      <p className="text-slate-300 text-sm leading-relaxed">{benefitTh}</p>
      <p className="text-slate-500 text-xs mt-1 leading-relaxed">{benefitEn}</p>
    </motion.div>
  );
}

// ─── Step Card ─────────────────────────────────────────────────────────────────

function StepCard({
  step,
  titleTh,
  titleEn,
  descTh,
}: {
  step: number;
  titleTh: string;
  titleEn: string;
  descTh: string;
}) {
  return (
    <motion.div variants={fadeUp} className="flex gap-4">
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-sm">
        {step}
      </div>
      <div className="pb-6 border-b border-white/5 last:border-0 flex-1">
        <h4 className="text-white font-semibold text-sm">{titleTh}</h4>
        <p className="text-slate-500 text-xs mb-1">{titleEn}</p>
        <p className="text-slate-400 text-sm leading-relaxed">{descTh}</p>
      </div>
    </motion.div>
  );
}

// ─── Section Wrapper ───────────────────────────────────────────────────────────

function Section({
  children,
  className = "",
  id,
}: {
  children: React.ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section
      id={id}
      className={`w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-28 ${className}`}
    >
      {children}
    </section>
  );
}

// ─── Section Heading ───────────────────────────────────────────────────────────

function SectionHeading({
  labelTh,
  labelEn,
  headingTh,
  headingEn,
  centered = false,
}: {
  labelTh: string;
  labelEn: string;
  headingTh: string;
  headingEn: string;
  centered?: boolean;
}) {
  return (
    <div className={`mb-12 ${centered ? "text-center" : ""}`}>
      <div
        className={`inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium mb-4 ${
          centered ? "mx-auto" : ""
        }`}
      >
        <span>{labelTh}</span>
        <span className="text-cyan-600">·</span>
        <span className="text-cyan-600">{labelEn}</span>
      </div>
      <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white mb-2">{headingTh}</h2>
      <p className="text-slate-400 text-sm sm:text-base">{headingEn}</p>
    </div>
  );
}

// ─── Navbar ────────────────────────────────────────────────────────────────────

function LandingNavbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.nav
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={`fixed top-4 left-4 right-4 z-50 max-w-7xl mx-auto rounded-2xl transition-all duration-300 ${
        scrolled
          ? "glass-panel"
          : "bg-transparent"
      }`}
    >
      <div className="flex items-center justify-between px-5 py-3">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center">
            <CloudRain className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <span className="text-white font-bold text-sm">ฝนมาแย้ง</span>
            <span className="hidden sm:inline text-slate-400 text-xs ml-2">Rain Nowcast</span>
          </div>
        </div>

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-6 text-sm text-slate-400">
          <a href="#features" className="hover:text-white transition-colors duration-200 cursor-pointer">
            คุณสมบัติ
          </a>
          <a href="#how-it-works" className="hover:text-white transition-colors duration-200 cursor-pointer">
            วิธีการทำงาน
          </a>
          <a href="#use-cases" className="hover:text-white transition-colors duration-200 cursor-pointer">
            การใช้งาน
          </a>
        </div>

        {/* CTA */}
        <div className="flex items-center gap-2">
          <a
            href="/dashboard"
            className="hidden sm:inline-flex items-center gap-1.5 text-sm text-slate-300 hover:text-white transition-colors duration-200 cursor-pointer px-3 py-1.5"
          >
            เข้าสู่ระบบ
          </a>
          <a
            href="#contact"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-900 text-sm font-semibold transition-colors duration-200 cursor-pointer"
          >
            ทดลองใช้ฟรี
            <ArrowRight className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </motion.nav>
  );
}

// ─── Main Landing Page ─────────────────────────────────────────────────────────

export default function LandingPage() {
  const shouldReduceMotion = useReducedMotion();

  const animProps = shouldReduceMotion
    ? { initial: "visible", whileInView: undefined }
    : { initial: "hidden", whileInView: "visible" };

  return (
    <div className="min-h-screen flex flex-col selection:bg-cyan-500/30 selection:text-cyan-200 overflow-x-hidden">
      <LandingNavbar />

      {/* ── HERO ──────────────────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex items-center justify-center pt-24 pb-16 overflow-hidden">
        {/* Background glow */}
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[700px] rounded-full bg-cyan-500/5 blur-3xl" />
          <div className="absolute top-1/3 right-0 w-96 h-96 rounded-full bg-blue-600/5 blur-3xl" />
        </div>

        <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col lg:flex-row items-center gap-12 lg:gap-20">
          {/* Left content */}
          <motion.div
            className="flex-1 text-center lg:text-left"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {/* Badge */}
            <motion.div variants={fadeUp} className="inline-flex items-center gap-2 mb-6">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium">
                <Activity className="w-3 h-3" />
                ระบบพยากรณ์ฝนแบบ Nowcast
              </span>
              <span className="text-slate-600 text-xs hidden sm:inline">Rain Nowcasting System</span>
            </motion.div>

            {/* Headline */}
            <motion.h1
              variants={fadeUp}
              className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-tight mb-4"
            >
              รู้ก่อน{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
                ฝนจะตก
              </span>
              <br />
              <span className="text-2xl sm:text-3xl lg:text-4xl text-slate-300 font-normal">
                ด้วยเรดาร์ กรมอุตุนิยมวิทยา
              </span>
            </motion.h1>
            <motion.p variants={fadeUp} className="text-slate-400 text-xs font-medium mb-2">
              Know Before It Rains · Powered by TMD Weather Radar
            </motion.p>

            {/* Subheading */}
            <motion.p
              variants={fadeUp}
              className="text-slate-300 text-base sm:text-lg leading-relaxed mb-8 max-w-xl lg:mx-0 mx-auto"
            >
              ระบบพยากรณ์ฝนระยะสั้น (Nowcast) แบบเรียลไทม์ ใช้ข้อมูลเรดาร์จากกรมอุตุนิยมวิทยา
              ติดตามการเคลื่อนที่ของฝนได้ล่วงหน้าสูงสุด 60 นาที พร้อมแจ้งเตือนอัตโนมัติ
            </motion.p>
            <motion.p variants={fadeUp} className="text-slate-500 text-sm leading-relaxed mb-10 max-w-xl lg:mx-0 mx-auto">
              Real-time rain nowcasting using TMD Doppler radar data. Track rainfall movement up to 60
              minutes ahead with automated push alerts.
            </motion.p>

            {/* CTAs */}
            <motion.div variants={fadeUp} className="flex flex-wrap gap-3 justify-center lg:justify-start">
              <a
                href="/dashboard"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-900 font-semibold text-sm transition-colors duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-2 focus:ring-offset-slate-950"
              >
                <Zap className="w-4 h-4" />
                เริ่มใช้งานฟรี · Try Free
                <ArrowRight className="w-4 h-4" />
              </a>
              <a
                href="#how-it-works"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl glass-panel hover:border-white/25 text-slate-300 hover:text-white font-medium text-sm transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-white/20"
              >
                วิธีการทำงาน · How It Works
                <ChevronDown className="w-4 h-4" />
              </a>
            </motion.div>

            {/* Trust bar */}
            <motion.div
              variants={fadeUp}
              className="mt-10 flex flex-wrap items-center gap-4 justify-center lg:justify-start"
            >
              {[
                { icon: Shield, text: "ข้อมูลจาก TMD โดยตรง" },
                { icon: Clock, text: "อัปเดตทุก 6 นาที" },
                { icon: Globe, text: "ครอบคลุมทั่วประเทศไทย" },
              ].map(({ icon: Icon, text }) => (
                <div key={text} className="flex items-center gap-1.5 text-slate-400 text-xs">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                  {text}
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* Right — radar visualization */}
          <motion.div
            className="flex-shrink-0 relative"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
          >
            <div className="glass-panel rounded-3xl p-6 sm:p-8 relative">
              {/* Status badge */}
              <div className="absolute -top-3 -right-3 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                LIVE
              </div>
              <RadarPulse />
              <div className="mt-4 text-center">
                <p className="text-slate-400 text-xs">ภาคกลาง · ฝนเบา 2 กม. ทิศตะวันตก</p>
                <p className="text-slate-600 text-xs">Central Region · Light rain 2km West</p>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Scroll hint */}
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2 text-slate-600"
          animate={{ y: [0, 6, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        >
          <ChevronDown className="w-5 h-5" />
        </motion.div>
      </section>

      {/* ── STATS ─────────────────────────────────────────────────────────── */}
      <section className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <motion.div
          className="grid grid-cols-2 lg:grid-cols-4 gap-4"
          variants={staggerContainer}
          {...animProps}
          viewport={{ once: true, margin: "-80px" }}
        >
          <StatCard value="85%+" label="ความแม่นยำ" sub="Forecast Accuracy" />
          <StatCard value="60 นาที" label="ล่วงหน้าสูงสุด" sub="Ahead Forecast" />
          <StatCard value="6 นาที" label="อัปเดตทุก" sub="Radar Update Cycle" />
          <StatCard value="18 สถานี" label="เรดาร์ทั่วไทย" sub="TMD Radar Stations" />
        </motion.div>
      </section>

      {/* ── FEATURES ──────────────────────────────────────────────────────── */}
      <Section id="features">
        <motion.div
          variants={staggerContainer}
          {...animProps}
          viewport={{ once: true, margin: "-80px" }}
        >
          <SectionHeading
            labelTh="คุณสมบัติหลัก"
            labelEn="Core Features"
            headingTh="ทุกสิ่งที่คุณต้องการ สำหรับการติดตามฝน"
            headingEn="Everything you need for real-time rainfall monitoring"
          />
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            <FeatureCard
              icon={Radar}
              titleTh="เรดาร์เรียลไทม์"
              titleEn="Real-Time Radar"
              descTh="แสดงภาพเรดาร์จาก กรมอุตุนิยมวิทยา อัปเดตทุก 6 นาที พร้อมสีแสดงความเข้มของฝน"
              descEn="Live TMD radar imagery updated every 6 minutes with rainfall intensity colormap."
            />
            <FeatureCard
              icon={Activity}
              titleTh="Nowcasting AI"
              titleEn="AI-Powered Nowcast"
              descTh="อัลกอริทึมติดตามการเคลื่อนที่ของกลุ่มฝน พยากรณ์ล่วงหน้าสูงสุด 60 นาที"
              descEn="Rainfall cell tracking algorithm forecasts rainfall movement up to 60 minutes ahead."
            />
            <FeatureCard
              icon={Bell}
              titleTh="แจ้งเตือนอัตโนมัติ"
              titleEn="Smart Alerts"
              descTh="รับการแจ้งเตือนผ่าน LINE หรือ Telegram เมื่อฝนกำลังจะตกในพื้นที่ของคุณ"
              descEn="Push notifications via LINE or Telegram when rain is approaching your location."
            />
            <FeatureCard
              icon={MapPin}
              titleTh="เลือกพื้นที่เฝ้าระวัง"
              titleEn="Location Watchlist"
              descTh="เพิ่มพื้นที่ที่ต้องการเฝ้าระวังได้หลายจุด ระบุรัศมีและเกณฑ์ความเข้มฝน"
              descEn="Monitor multiple locations with configurable radius and rainfall intensity thresholds."
            />
            <FeatureCard
              icon={BarChart3}
              titleTh="สถิติและประวัติฝน"
              titleEn="Rainfall History & Analytics"
              descTh="ดูประวัติการตกของฝน แนวโน้ม และข้อมูลสถิติย้อนหลัง"
              descEn="Historical rainfall records, trends, and statistical summaries for any area."
            />
            <FeatureCard
              icon={Globe}
              titleTh="API สำหรับนักพัฒนา"
              titleEn="Developer API"
              descTh="เชื่อมต่อข้อมูล Nowcast เข้ากับแอปพลิเคชันของคุณผ่าน REST API"
              descEn="Integrate nowcast data directly into your applications via our REST API."
            />
          </div>
        </motion.div>
      </Section>

      {/* ── HOW IT WORKS ──────────────────────────────────────────────────── */}
      <Section id="how-it-works">
        <motion.div
          className="grid lg:grid-cols-2 gap-16 items-center"
          variants={staggerContainer}
          {...animProps}
          viewport={{ once: true, margin: "-80px" }}
        >
          <div>
            <SectionHeading
              labelTh="วิธีการทำงาน"
              labelEn="How It Works"
              headingTh="จากเรดาร์ สู่การแจ้งเตือน ใน 6 นาที"
              headingEn="From radar data to alert in 6 minutes"
            />
            <div className="space-y-1">
              <StepCard
                step={1}
                titleTh="รับข้อมูลเรดาร์จาก TMD"
                titleEn="Ingest TMD radar feed"
                descTh="ดึงข้อมูลเรดาร์ดอปเปลอร์ดิบจากกรมอุตุนิยมวิทยาทุก 6 นาที ครอบคลุม 18 สถานีทั่วประเทศ"
              />
              <StepCard
                step={2}
                titleTh="ประมวลผลและตีความข้อมูล"
                titleEn="Process & decode radar reflectivity"
                descTh="แปลงค่า reflectivity (dBZ) เป็นอัตราการตกของฝน (mm/hr) และสร้างแผนที่ภาพรวม"
              />
              <StepCard
                step={3}
                titleTh="ติดตามการเคลื่อนที่ของกลุ่มฝน"
                titleEn="Track rainfall cell movement"
                descTh="อัลกอริทึม Optical Flow และ Cell Tracking คำนวณทิศทางและความเร็วการเคลื่อนที่ของกลุ่มฝน"
              />
              <StepCard
                step={4}
                titleTh="พยากรณ์และแจ้งเตือน"
                titleEn="Forecast & notify"
                descTh="ประมาณตำแหน่งกลุ่มฝนในอีก 10–60 นาที และส่งการแจ้งเตือนไปยังพื้นที่ที่ได้รับผลกระทบ"
              />
            </div>
          </div>

          {/* Pipeline visual */}
          <div className="glass-panel rounded-3xl p-6 space-y-3">
            {[
              { icon: CloudRain, label: "TMD Radar Feed", sublabel: "18 stations · dBZ reflectivity", color: "#22d3ee" },
              { icon: Activity, label: "Signal Processing", sublabel: "dBZ → mm/hr · composite merge", color: "#60a5fa" },
              { icon: Radar, label: "Cell Tracking", sublabel: "Optical Flow · motion vectors", color: "#a78bfa" },
              { icon: Bell, label: "Nowcast + Alert", sublabel: "T+10 to T+60 min forecast", color: "#34d399" },
            ].map((item, i) => (
              <motion.div key={item.label} variants={fadeUp}>
                <div className="flex items-center gap-3 p-4 rounded-xl bg-white/3 border border-white/5 hover:border-white/10 transition-colors duration-200">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: `${item.color}15`, border: `1px solid ${item.color}25` }}
                  >
                    <item.icon className="w-5 h-5" style={{ color: item.color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white text-sm font-semibold">{item.label}</p>
                    <p className="text-slate-500 text-xs truncate">{item.sublabel}</p>
                  </div>
                  <div className="w-2 h-2 rounded-full" style={{ background: item.color, opacity: 0.6 }} />
                </div>
                {i < 3 && (
                  <div className="flex justify-center py-1">
                    <div className="w-px h-4 bg-white/10" />
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </motion.div>
      </Section>

      {/* ── USE CASES ─────────────────────────────────────────────────────── */}
      <Section id="use-cases">
        <motion.div
          variants={staggerContainer}
          {...animProps}
          viewport={{ once: true, margin: "-80px" }}
        >
          <SectionHeading
            labelTh="การใช้งาน"
            labelEn="Use Cases"
            headingTh="เหมาะสำหรับทุกภาคส่วน"
            headingEn="Built for every industry that depends on the weather"
            centered
          />
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <UseCaseCard
              icon={Building2}
              sectorTh="ภาคธุรกิจและอุตสาหกรรม"
              sectorEn="Business & Industry"
              benefitTh="วางแผนการผลิต การขนส่ง และกิจกรรมกลางแจ้งล่วงหน้า ลดความเสียหายจากฝน"
              benefitEn="Plan production, logistics, and outdoor ops. Minimize weather-related disruptions."
              color="#60a5fa"
            />
            <UseCaseCard
              icon={Plane}
              sectorTh="การบินและโลจิสติกส์"
              sectorEn="Aviation & Logistics"
              benefitTh="ติดตามสภาพอากาศแบบเรียลไทม์ สนับสนุนการตัดสินใจในการปฏิบัติการ"
              benefitEn="Real-time weather awareness for operational decision-making and safety."
              color="#a78bfa"
            />
            <UseCaseCard
              icon={Truck}
              sectorTh="การเกษตร"
              sectorEn="Agriculture"
              benefitTh="วางแผนการเพาะปลูก เก็บเกี่ยว และจัดการน้ำได้แม่นยำยิ่งขึ้น"
              benefitEn="Optimize planting, harvest schedules, and irrigation with precise rain forecasts."
              color="#34d399"
            />
            <UseCaseCard
              icon={Leaf}
              sectorTh="หน่วยงานภาครัฐ"
              sectorEn="Government & Emergency"
              benefitTh="สนับสนุนการบริหารจัดการน้ำท่วม การแจ้งเตือนภัย และการตอบสนองฉุกเฉิน"
              benefitEn="Flood management, disaster warning, and emergency response coordination."
              color="#fb923c"
            />
          </div>
        </motion.div>
      </Section>

      {/* ── CTA ───────────────────────────────────────────────────────────── */}
      <section id="contact" className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-28">
        <motion.div
          className="glass-panel rounded-3xl p-10 sm:p-16 text-center relative overflow-hidden"
          initial={{ opacity: 0, y: 32 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
        >
          {/* BG glow */}
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] rounded-full bg-cyan-500/5 blur-3xl" />
          </div>

          <div className="relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium mb-6">
              <Users className="w-3 h-3" />
              เปิดรับผู้ใช้งานรุ่นทดสอบ · Early Access
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              พร้อมรู้ก่อนฝนจะตกแล้วหรือยัง?
            </h2>
            <p className="text-slate-400 text-base mb-2">Ready to stay one step ahead of the rain?</p>
            <p className="text-slate-400 text-sm mb-10 max-w-xl mx-auto leading-relaxed">
              ลงทะเบียนเพื่อรับสิทธิ์เข้าถึงระบบก่อนใคร พร้อมรับการแจ้งเตือนฟรีในช่วงทดสอบ
            </p>

            <div className="flex flex-col sm:flex-row gap-3 justify-center max-w-md mx-auto">
              <a
                href="/dashboard"
                className="flex-1 inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-900 font-semibold text-sm transition-colors duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-2 focus:ring-offset-slate-950"
              >
                <Zap className="w-4 h-4" />
                เข้าใช้งาน Dashboard
              </a>
              <a
                href="mailto:contact@fonmayang.app"
                className="flex-1 inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl border border-white/15 hover:border-white/30 text-slate-300 hover:text-white font-medium text-sm transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-white/20"
              >
                ติดต่อเรา · Contact Us
              </a>
            </div>

            <p className="text-slate-600 text-xs mt-6">
              ไม่ต้องใช้บัตรเครดิต · Free during beta · ข้อมูลปลอดภัย
            </p>
          </div>
        </motion.div>
      </section>

      {/* ── FOOTER ────────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/5 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center">
              <CloudRain className="w-3.5 h-3.5 text-cyan-400" />
            </div>
            <span className="text-slate-400 text-sm">
              ฝนมาแย้ง · FonMaYang Rain Nowcast System
            </span>
          </div>
          <div className="flex items-center gap-4 text-slate-600 text-xs">
            <span>ข้อมูลจาก กรมอุตุนิยมวิทยา (TMD)</span>
            <span>·</span>
            <span>&copy; 2026</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
