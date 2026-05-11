import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Upload, FileText, Zap, BarChart3, Download, ArrowRight, CheckCircle, Clock, Users, Building, Shield, Globe, Code, Database, Target, Play, Lock, Gauge, DollarSign, Settings, Workflow, Scale, FileCheck, Server, Briefcase, X } from 'lucide-react';
import { SEO } from '@/components/seo';

const QGenProductPage: React.FC = () => {
  const [activeDemo, setActiveDemo] = useState(0);
  const [showDemoModal, setShowDemoModal] = useState(false);

  // Static color class mappings to avoid Tailwind purging issues
  const colorClasses = {
    blue: {
      bg: "bg-blue-100",
      text: "text-blue-600",
      hover: "group-hover:bg-blue-200"
    },
    green: {
      bg: "bg-green-100",
      text: "text-green-600",
      hover: "group-hover:bg-green-200"
    },
    purple: {
      bg: "bg-purple-100",
      text: "text-purple-600",
      hover: "group-hover:bg-purple-200"
    },
    orange: {
      bg: "bg-orange-100",
      text: "text-orange-600",
      hover: "group-hover:bg-orange-200"
    },
    red: {
      bg: "bg-red-100",
      text: "text-red-600",
      hover: "group-hover:bg-red-200"
    },
    indigo: {
      bg: "bg-indigo-100",
      text: "text-indigo-600",
      hover: "group-hover:bg-indigo-200"
    },
    teal: {
      bg: "bg-teal-100",
      text: "text-teal-600",
      hover: "group-hover:bg-teal-200"
    },
    cyan: {
      bg: "bg-cyan-100",
      text: "text-cyan-600",
      hover: "group-hover:bg-cyan-200"
    },
    pink: {
      bg: "bg-pink-100",
      text: "text-pink-600",
      hover: "group-hover:bg-pink-200"
    },
    amber: {
      bg: "bg-amber-100",
      text: "text-amber-600",
      hover: "group-hover:bg-amber-200"
    }
  };

  const demoSteps = [
    {
      title: "Upload Documents",
      description: "Drag and drop your files or upload multiple documents",
      image: "/images/qgen-upload-demo.png"
    },
    {
      title: "AI Processing",
      description: "Our AI analyzes content and generates optimal schemas",
      image: "/images/qgen-processing-demo.png"
    },
    {
      title: "Export Results",
      description: "Download your synthetic datasets in multiple formats",
      image: "/images/qgen-export-demo.png"
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <SEO
        title="QGen — Document Processing & AI Training Data Platform"
        description="Transform any document into high-quality synthetic Q&A datasets for AI model training. Upload PDFs, Word docs, images and get structured training data in minutes."
        keywords="QGen, document processing, AI training data, synthetic datasets, Q&A generation, PDF processing, document AI, machine learning training data"
      />

      {/* Hero Section */}
      <section className="bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 text-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center bg-blue-500/20 text-blue-300 px-4 py-2 rounded-full text-sm font-medium mb-6">
                <Upload className="h-4 w-4 mr-2" />
                Document Processing Platform
              </div>
              <h1 className="text-5xl lg:text-6xl font-bold mb-6 leading-tight">
                QGen
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400"> Transforms</span> Documents
              </h1>
              <p className="text-xl text-gray-300 mb-8 max-w-2xl">
                Upload any document and get high-quality synthetic Q&A datasets for AI model training. 
                Used by startups to Fortune 500 companies worldwide.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 mb-8">
                <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-6 text-lg" onClick={() => window.location.href = 'mailto:hello@qgen.dev'}>
                  Request Invitation
                </Button>
                <Button 
                  variant="outline" 
                  size="lg" 
                  className="border-white/30 text-white bg-transparent hover:bg-white hover:text-blue-900 font-semibold px-8 py-6 text-lg"
                  onClick={() => setShowDemoModal(true)}
                >
                  <Play className="h-5 w-5" />
                  Watch Demo
                </Button>
              </div>
              <div className="text-sm text-gray-400">
                Ô£à Free tier available ÔÇó Ô£à No credit card required ÔÇó Ô£à Setup in 2 minutes
              </div>
            </div>
            
            {/* Product Demo GIF */}
            <div className="lg:block">
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20">
                <div className="bg-white rounded-xl shadow-2xl overflow-hidden">
                  <div className="flex items-center gap-2 p-4 bg-gray-50 border-b">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                      <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    </div>
                    <span className="text-gray-600 text-xs font-medium">QGen Workflow</span>
                  </div>
                  
                  <div className="aspect-video p-4">
                    <img
                      src="/images/interactiveDemo.gif"
                      alt="QGen Workflow Demo - Upload documents, AI processing, and export Q&A datasets"
                      className="w-full h-full object-cover rounded-lg"
                      loading="lazy"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
              Everything You Need for AI Training Data
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              QGen provides a complete platform for transforming documents into high-quality synthetic datasets.
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                icon: Upload,
                title: "Smart Document Processing",
                description: "Upload PDF, Word, Excel, PowerPoint, and images. OCR automatically extracts text from scanned documents.",
                color: "blue"
              },
              {
                icon: BarChart3,
                title: "AI Schema Generation",
                description: "Intelligent field detection creates optimal data structures automatically. Customize schemas for your specific needs.",
                color: "green"
              },
              {
                icon: Zap,
                title: "Batch Processing",
                description: "Process up to 100 documents simultaneously. Parallel processing ensures fast turnaround times.",
                color: "purple"
              },
              {
                icon: Target,
                title: "Multi-Dimensional Quality Analysis",
                description: "Comprehensive scoring across 4 quality dimensions: completeness, structure, grounding, and coverage with real-time validation.",
                color: "orange"
              },
              {
                icon: Shield,
                title: "Enterprise Security",
                description: "Enterprise-grade security infrastructure. On-premise deployment available for sensitive data requirements.",
                color: "red"
              },
              {
                icon: Code,
                title: "Multiple Export Formats",
                description: "Export datasets in JSON, CSV, XML, or SQL formats. API access for seamless integration.",
                color: "indigo"
              }
            ].map((feature, idx) => (
              <Card key={idx} className="text-center p-6 border-0 shadow-lg hover:shadow-xl transition-shadow">
                <div className={`w-16 h-16 ${colorClasses[feature.color as keyof typeof colorClasses].bg} rounded-2xl flex items-center justify-center mx-auto mb-6`}>
                  <feature.icon className={`h-8 w-8 ${colorClasses[feature.color as keyof typeof colorClasses].text}`} />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Demo Section */}
      <section id="demo" className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
              See QGen in Action
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Watch how QGen transforms your documents into AI training datasets in just three simple steps.
            </p>
          </div>

          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              {demoSteps.map((step, idx) => (
                <div
                  key={idx}
                  className={`cursor-pointer transition-all duration-300 rounded-xl p-6 ${
                    activeDemo === idx
                      ? 'bg-blue-50 border-2 border-blue-300 shadow-lg'
                      : 'bg-white border-2 border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setActiveDemo(idx)}
                >
                  <div className="flex items-start gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                      activeDemo === idx ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
                    }`}>
                      {idx + 1}
                    </div>
                    <div>
                      <h3 className={`font-semibold text-lg mb-2 ${
                        activeDemo === idx ? 'text-blue-900' : 'text-gray-900'
                      }`}>
                        {step.title}
                      </h3>
                      <p className="text-gray-600">{step.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-white rounded-2xl shadow-2xl p-8">
              <div className="aspect-video bg-gradient-to-br from-blue-100 to-purple-100 rounded-xl flex items-center justify-center">
                <div className="text-center">
                  <Play className="h-16 w-16 text-blue-600 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    {demoSteps[activeDemo].title}
                  </h3>
                  <p className="text-gray-600 mb-6">
                    {demoSteps[activeDemo].description}
                  </p>
                  <Button 
                    className="bg-blue-600 hover:bg-blue-700"
                    onClick={() => setShowDemoModal(true)}
                  >
                    Watch Full Demo
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
              Built for Every Use Case
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              From startup MVPs to enterprise AI initiatives, QGen adapts to your specific requirements.
            </p>
          </div>

          <Tabs defaultValue="startups" className="space-y-8">
            <TabsList className="grid w-full grid-cols-3 max-w-md mx-auto">
              <TabsTrigger value="startups">Startups</TabsTrigger>
              <TabsTrigger value="datascience">Data Science</TabsTrigger>
              <TabsTrigger value="enterprise">Enterprise</TabsTrigger>
            </TabsList>

            <TabsContent value="startups" className="space-y-8">
              <Card className="p-8">
                <div className="grid lg:grid-cols-2 gap-8 items-center">
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900 mb-4">Perfect for MVP Development</h3>
                    <p className="text-gray-600 mb-6">
                      Quickly generate training data for your AI prototypes without expensive data collection. 
                      Get from idea to demo in days, not months.
                    </p>
                    <div className="space-y-4">
                      <div className="flex items-center gap-3">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span>Free tier with generous limits</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span>Fast iteration and experimentation</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span>Scale pricing as you grow</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-blue-50 rounded-xl p-6">
                    <h4 className="font-semibold text-blue-900 mb-4">Example: ChatBot Training</h4>
                    <p className="text-blue-700 text-sm mb-4">
                      Upload your product documentation and generate thousands of customer Q&A pairs 
                      to train your customer service chatbot.
                    </p>
                    <div className="bg-white rounded p-3 text-xs font-mono">
                      <div className="text-blue-600">Input:</div>
                      <div className="text-gray-600 mb-2">product_manual.pdf (2.3MB)</div>
                      <div className="text-green-600">Output:</div>
                      <div className="text-gray-600">2,847 Q&A pairs ÔÇó 98.2% accuracy</div>
                    </div>
                  </div>
                </div>
              </Card>
            </TabsContent>

            <TabsContent value="datascience" className="space-y-8">
              <Card className="p-8">
                <div className="grid lg:grid-cols-2 gap-8 items-center">
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900 mb-4">Advanced Model Training</h3>
                    <p className="text-gray-600 mb-6">
                      Generate domain-specific datasets for specialized AI models. Custom schemas and 
                      validation ensure high-quality training data for your research.
                    </p>
                    <div className="space-y-4">
                      <div className="flex items-center gap-3">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span>Custom schema definition and refinement</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span>Confidence scoring and quality metrics</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span>API integration for automated workflows</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-green-50 rounded-xl p-6">
                    <h4 className="font-semibold text-green-900 mb-4">Example: Medical AI Research</h4>
                    <p className="text-green-700 text-sm mb-4">
                      Process medical literature and generate structured datasets for training 
                      diagnostic AI models while maintaining data privacy.
                    </p>
                    <div className="bg-white rounded p-3 text-xs font-mono">
                      <div className="text-green-600">Processing:</div>
                      <div className="text-gray-600 mb-2">127 research papers ÔÇó 45MB</div>
                      <div className="text-green-600">Generated:</div>
                      <div className="text-gray-600">15,432 symptom-diagnosis pairs</div>
                    </div>
                  </div>
                </div>
              </Card>
            </TabsContent>

            <TabsContent value="enterprise" className="space-y-8">
              <Card className="p-8">
                <div className="grid lg:grid-cols-2 gap-8 items-center">
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900 mb-4">Enterprise-Scale Operations</h3>
                    <p className="text-gray-600 mb-6">
                      Process thousands of documents with enterprise security, compliance, and 
                      dedicated support. On-premise deployment for sensitive data requirements.
                    </p>
                    <div className="space-y-4">
                      <div className="flex items-center gap-3">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span>Enterprise security and data sovereignty</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span>Dedicated support and training</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <CheckCircle className="h-5 w-5 text-green-600" />
                        <span>Custom integrations and workflows</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-purple-50 rounded-xl p-6">
                    <h4 className="font-semibold text-purple-900 mb-4">Example: Legal Document Analysis</h4>
                    <p className="text-purple-700 text-sm mb-4">
                      Fortune 500 law firm processes 50,000+ contracts to train AI for 
                      automated clause detection and risk assessment.
                    </p>
                    <div className="bg-white rounded p-3 text-xs font-mono">
                      <div className="text-purple-600">Scale:</div>
                      <div className="text-gray-600 mb-2">50,000 contracts ÔÇó 2.3TB processed</div>
                      <div className="text-purple-600">Output:</div>
                      <div className="text-gray-600">1.2M clause-risk pairs ÔÇó 96.7% accuracy</div>
                    </div>
                  </div>
                </div>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </section>

      {/* On-Premise Deployment Section */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <div className="inline-flex items-center bg-blue-100 text-blue-800 px-4 py-2 rounded-full text-sm font-medium mb-6">
              <Server className="h-4 w-4 mr-2" />
              Enterprise On-Premise Solution
            </div>
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
              Complete Control with On-Premise Deployment
            </h2>
            <p className="text-xl text-gray-600 max-w-4xl mx-auto">
              Deploy QGen within your infrastructure for maximum security, compliance, and control. 
              Perfect for organizations with strict data sovereignty and regulatory requirements.
            </p>
          </div>

          {/* Benefits Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-6 mb-16">
            {[
              {
                icon: Lock,
                title: "Privacy & Data Sovereignty",
                description: "Keep all data within your infrastructure. Zero external data transfer ensures complete privacy control.",
                color: "blue"
              },
              {
                icon: Shield,
                title: "Security & Access Control",
                description: "Integrate with your existing security protocols, SSO, and access management systems.",
                color: "green"
              },
              {
                icon: Gauge,
                title: "Performance & Latency",
                description: "Optimize processing speeds with dedicated hardware and eliminate network latency issues.",
                color: "purple"
              },
              {
                icon: DollarSign,
                title: "Cost Predictability",
                description: "Fixed licensing costs with no usage-based fees. Predictable budgeting for enterprise planning.",
                color: "orange"
              },
              {
                icon: Settings,
                title: "Customization & Control",
                description: "Tailor the platform to your specific workflows, branding, and business requirements.",
                color: "indigo"
              },
              {
                icon: Workflow,
                title: "Legacy System Integration",
                description: "Seamlessly connect with existing enterprise systems, databases, and workflows.",
                color: "red"
              },
              {
                icon: FileCheck,
                title: "Regulatory Compliance",
                description: "Meet GDPR, HIPAA, SOX, and industry-specific compliance requirements with confidence.",
                color: "teal"
              },
              {
                icon: Server,
                title: "Reliability & Availability",
                description: "Ensure 99.9% uptime with redundant systems and dedicated infrastructure management.",
                color: "cyan"
              },
              {
                icon: Scale,
                title: "Scalability on Your Terms",
                description: "Scale processing power based on your needs without external dependencies or limits.",
                color: "pink"
              },
              {
                icon: Database,
                title: "Data Retention & Auditability",
                description: "Complete audit trails and long-term data retention policies aligned with your governance.",
                color: "amber"
              }
            ].map((benefit, idx) => (
              <Card key={idx} className="text-center p-6 border-0 shadow-lg hover:shadow-xl transition-shadow group hover:scale-105 duration-300">
                <div className={`w-12 h-12 ${colorClasses[benefit.color as keyof typeof colorClasses].bg} rounded-2xl flex items-center justify-center mx-auto mb-4 ${colorClasses[benefit.color as keyof typeof colorClasses].hover} transition-colors`}>
                  <benefit.icon className={`h-6 w-6 ${colorClasses[benefit.color as keyof typeof colorClasses].text}`} />
                </div>
                <h3 className="text-sm font-semibold text-gray-900 mb-3 leading-tight">{benefit.title}</h3>
                <p className="text-xs text-gray-600 leading-relaxed">{benefit.description}</p>
              </Card>
            ))}
          </div>

          {/* Implementation Process */}
          <div className="bg-white rounded-2xl p-8 shadow-xl mb-16">
            <h3 className="text-2xl font-bold text-gray-900 mb-8 text-center">Seamless Implementation Process</h3>
            <div className="grid md:grid-cols-4 gap-8">
              {[
                {
                  step: "1",
                  title: "Requirements Analysis",
                  description: "Infrastructure assessment and custom requirements gathering with our enterprise team.",
                  duration: "1-2 weeks"
                },
                {
                  step: "2", 
                  title: "Custom Configuration",
                  description: "Platform customization, security integration, and system compatibility testing.",
                  duration: "2-3 weeks"
                },
                {
                  step: "3",
                  title: "Deployment & Training",
                  description: "Installation, configuration, and comprehensive team training with dedicated support.",
                  duration: "1-2 weeks"
                },
                {
                  step: "4",
                  title: "Ongoing Support",
                  description: "24/7 enterprise support, maintenance, updates, and performance optimization.",
                  duration: "Continuous"
                }
              ].map((process, idx) => (
                <div key={idx} className="text-center">
                  <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-lg mx-auto mb-4">
                    {process.step}
                  </div>
                  <h4 className="font-semibold text-gray-900 mb-2">{process.title}</h4>
                  <p className="text-sm text-gray-600 mb-2">{process.description}</p>
                  <span className="text-xs text-blue-600 font-medium">{process.duration}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Enterprise Features */}
          <div className="grid lg:grid-cols-2 gap-12 items-center mb-16">
            <div>
              <h3 className="text-2xl font-bold text-gray-900 mb-6">Enterprise-Grade Features</h3>
              <div className="space-y-4">
                {[
                  "Single Sign-On (SSO) integration with SAML, LDAP, Active Directory",
                  "Role-based access controls with granular permissions",
                  "Custom data retention policies and automated archiving",
                  "Advanced monitoring, logging, and performance analytics",
                  "White-label customization with your branding and workflows",
                  "High-availability deployment with automatic failover",
                  "Dedicated enterprise support with guaranteed SLA",
                  "Custom API endpoints and webhook integrations"
                ].map((feature, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-700">{feature}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl p-8">
              <div className="text-center">
                <Briefcase className="h-16 w-16 text-blue-600 mx-auto mb-6" />
                <h4 className="text-xl font-bold text-gray-900 mb-4">Ready for Enterprise?</h4>
                <p className="text-gray-600 mb-6">
                  Join Fortune 500 companies using QGen on-premise for their mission-critical AI training data needs.
                </p>
                <div className="space-y-3">
                  <Button size="lg" className="w-full bg-blue-600 hover:bg-blue-700" onClick={() => window.location.href = 'mailto:hello@qgen.dev'}>
                    Contact Enterprise Sales
                  </Button>
                  <Button variant="outline" size="lg" className="w-full" onClick={() => window.location.href = 'https://calendly.com/raghavarora/30min'}>
                    Schedule Technical Demo
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* Compliance & Security */}
          <div className="bg-gradient-to-r from-gray-900 to-blue-900 text-white rounded-2xl p-8">
            <div className="text-center mb-8">
              <Shield className="h-12 w-12 text-blue-400 mx-auto mb-4" />
              <h3 className="text-2xl font-bold mb-4">Security & Compliance First</h3>
              <p className="text-blue-100 max-w-3xl mx-auto">
                Built with enterprise security standards and compliance frameworks to meet the most stringent requirements.
              </p>
            </div>
            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center">
                <h4 className="font-semibold text-white mb-3">Data Protection</h4>
                <ul className="text-sm text-blue-100 space-y-1">
                  <li>ÔÇó End-to-end encryption at rest and in transit</li>
                  <li>ÔÇó Zero-knowledge architecture</li>
                  <li>ÔÇó Secure key management</li>
                  <li>ÔÇó Regular security audits</li>
                </ul>
              </div>
              <div className="text-center">
                <h4 className="font-semibold text-white mb-3">Compliance Ready</h4>
                <ul className="text-sm text-blue-100 space-y-1">
                  <li>ÔÇó GDPR and CCPA compliant</li>
                  <li>ÔÇó HIPAA ready for healthcare</li>
                  <li>ÔÇó SOX compliance for financial services</li>
                  <li>ÔÇó Industry-specific certifications</li>
                </ul>
              </div>
              <div className="text-center">
                <h4 className="font-semibold text-white mb-3">Enterprise Controls</h4>
                <ul className="text-sm text-blue-100 space-y-1">
                  <li>ÔÇó Advanced threat detection</li>
                  <li>ÔÇó Automated backup and recovery</li>
                  <li>ÔÇó Comprehensive audit logging</li>
                  <li>ÔÇó Disaster recovery planning</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
            Early Access Program
          </h2>
          <p className="text-xl text-gray-600 mb-12">
            Join our invitation-only beta program and help shape the future of document-to-AI-data transformation.
          </p>
          
          <div className="grid md:grid-cols-3 gap-8">
            <Card className="p-6 border-2">
              <div className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-sm font-medium mb-4 inline-block">
                Invitation Only
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">Beta Access</h3>
              <p className="text-gray-600 mb-6">Perfect for getting started with QGen</p>
              <ul className="text-sm text-gray-600 space-y-2 mb-6">
                <li>ÔÇó Core QGen features</li>
                <li>ÔÇó Beta testing participation</li>
                <li>ÔÇó Community feedback channel</li>
                <li>ÔÇó Early feature previews</li>
                <li>ÔÇó Documentation access</li>
              </ul>
              <Button className="w-full" variant="outline" onClick={() => window.location.href = 'mailto:hello@qgen.dev'}>
                Request Invitation
              </Button>
            </Card>
            
            <Card className="p-6 border-2 border-blue-500 relative">
              <div className="bg-orange-100 text-gray-700 px-3 py-1 rounded-full text-sm font-medium mb-4 inline-block">
                Priority Access
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">Enterprise Beta</h3>
              <p className="text-gray-600 mb-6">For teams and organizations</p>
              <ul className="text-sm text-gray-600 space-y-2 mb-6">
                <li>ÔÇó All beta features</li>
                <li>ÔÇó Priority support</li>
                <li>ÔÇó Early enterprise features</li>
                <li>ÔÇó Dedicated feedback sessions</li>
                <li>ÔÇó Custom implementation guidance</li>
              </ul>
              <Button className="w-full bg-blue-600 hover:bg-blue-700" onClick={() => window.location.href = 'mailto:hello@qgen.dev'}>
                Schedule Call
              </Button>
            </Card>
            
            <Card className="p-6 border-2">
              <div className="bg-purple-100 text-purple-700 px-3 py-1 rounded-full text-sm font-medium mb-4 inline-block">
                Partnership
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">Custom Solutions</h3>
              <p className="text-gray-600 mb-6">For large-scale implementations</p>
              <ul className="text-sm text-gray-600 space-y-2 mb-6">
                <li>ÔÇó Custom implementation</li>
                <li>ÔÇó On-premise deployment</li>
                <li>ÔÇó Dedicated support team</li>
                <li>ÔÇó Co-development opportunities</li>
                <li>ÔÇó White-label solutions</li>
              </ul>
              <Button className="w-full" variant="outline" onClick={() => window.location.href = 'mailto:hello@qgen.dev'}>
                Discuss Partnership
              </Button>
            </Card>
          </div>
          
          <div className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-sm text-blue-800 text-center">
              <strong>Note:</strong> Public pricing will be announced closer to general availability. Early access participants receive preferential pricing.
            </p>
          </div>
          
          <div className="mt-12">
            <Button size="lg" className="bg-blue-600 hover:bg-blue-700 mr-4" onClick={() => window.location.href = 'mailto:hello@qgen.dev'}>
              Request Invitation
            </Button>
            <Button variant="outline" size="lg" onClick={() => window.location.href = 'mailto:hello@qgen.dev'}>
              Contact Sales
            </Button>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 bg-gradient-to-r from-blue-600 to-purple-600 text-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Transform Your Documents?</h2>
          <p className="text-xl text-blue-100 mb-8">
            Transform your documents into high-quality AI training data with QGen.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button asChild size="lg" className="bg-white text-blue-600 hover:bg-gray-100 font-semibold px-8 py-6 text-lg">
              <a href="https://github.com/arora-raghav/qgen">Star on GitHub</a>
            </Button>
            <Button asChild variant="outline" size="lg" className="border-white/30 text-white bg-transparent hover:bg-white hover:text-blue-900 font-semibold px-8 py-6 text-lg">
              <a href="https://calendly.com/raghavarora/30min">Schedule Demo</a>
            </Button>
          </div>
        </div>
      </section>
      
      {/* Demo Modal */}
      {showDemoModal && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setShowDemoModal(false)}
        >
          <div 
            className="relative bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <button 
              onClick={() => setShowDemoModal(false)}
              className="absolute top-4 right-4 z-10 bg-black bg-opacity-50 text-white rounded-full p-2 hover:bg-opacity-75 transition-all"
            >
              <X className="h-6 w-6" />
            </button>
            <div className="aspect-video">
              <iframe
                src="https://www.youtube.com/embed/x3DgDP6QDBo?autoplay=1"
                title="QGen Demo Video"
                className="w-full h-full"
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QGenProductPage;
