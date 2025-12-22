# Project: Embedded DSP Development System

## Project Overview

Create an ecosystem for Audio algorithms created in Python to be painlessly ported to realtime (low latency) embedded platform. Also facilitate the reuse of DSP blocks in the algorithms

## Development Instructions

See Current Focus below. At this point we will be modifying the Project Concept Document and Development Journal, creating some mid level module specfications and proof of concept code. Periodically we will clear the Development Journal at informal review points.

Let's keep a Development Journal as we work, to capture discussions that might not normally end up in a document. Perhaps we can clear this journal periodically. This journal will replace the context that normally is part of a chat based AI session. When claud code fires up, it will read this journal to establish context

## Current Focus
We are working on this project in an iterative way. In the project concept document, we will be discuss things at a high level,information that would normally be included in a requirements or high level architecture document. There is no point in fleshing  specific interface or class definitions at this level of documentation. We identify entities that are important conceptually, we talk about relationships and concepts, the focus is on creating what amounts to a blend of requirements and high level architecture. Where needed to prove out proof on concept or clarify thinking or generating intermediate level specifications, we generate code and flesh out modules specs.

**Conceptual Communication Style**: For the Product Concept Documet, maintain a high level of abstraction focused on concepts and relationships rather than implementation details. Avoid diving into specific examples, formal specifications, or implementation patterns unless explicitly requested. The goal is to gently introduce ideas to help readers understand the conceptual framework, not to provide coding-ready specifications. When in doubt, stay at the concept level - detailed specifications can always be added later when moving toward implementation.

## File Organization
- **Project Concept.md** - High-level goals, concepts, and architecture
- **Graph Preparation Design.md** - Intermediate design details for graph preparation (processing order, signal specs, buffer allocation)
- **Module Spec.md** - Detailed class specifications
- **Development Journal.md** - Exploration and discussions

## Custom Instructions for Claude

For Pyhon code, Use the instructions in Python Coding Standards.md